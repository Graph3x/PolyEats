import argparse
import json
import sys
from pathlib import Path

VERSION = "1.1.1"


class SchemaException(Exception):
    pass


class PipelineException(Exception):
    pass


class SubmissionException(Exception):
    pass


class Grader:
    def __init__(self, dataset_path: str):
        self.dataset = dataset_path
        self.nodes = None
        self.edges = None

    def load(self, submission_path: str) -> None:
        with open(submission_path, "r") as f:
            submission = json.load(f)

        with open(self.dataset, "r") as f:
            truth = json.load(f)

        if truth.get("schema_version", "") != VERSION:
            raise SchemaException("Dataset schema doesnt match grader!")

        self.dataset_version = truth["dataset_version"]
        self.nodes = truth["nodes"]
        self.edges = truth["edges"]

        self._validate(submission)
        self.submitted_nodes = submission["nodes"]
        self.submitted_edges = submission["edges"]

    @staticmethod
    def _validate(submission) -> None:
        if not isinstance(submission, dict):
            raise SubmissionException("submission must be a JSON object")

        nodes = submission.get("nodes")
        if not isinstance(nodes, list) or not all(isinstance(x, str) for x in nodes):
            raise SubmissionException("'nodes' must be a list of node id strings")

        edges = submission.get("edges")
        if not isinstance(edges, list) or not all(
            isinstance(x, dict)
            and isinstance(x.get("caller"), str)
            and isinstance(x.get("callee"), str)
            for x in edges
        ):
            raise SubmissionException(
                "'edges' must be a list of objects with string 'caller' and 'callee'"
            )

        unknown = {x[key] for x in edges for key in ("caller", "callee")} - set(nodes)
        if unknown:
            raise SubmissionException(
                f"edges reference nodes missing from 'nodes': {sorted(unknown)}"
            )

    def _score_base(self, nodes: list[dict], edges: list[dict]):

        if {x["id"] for x in nodes} != set(self.submitted_nodes):
            print(
                "You have a node mismatch - this generally shouldnt happen.\n"
                "Please check that your naming convention matches the folder names",
                file=sys.stderr,
            )

        truth = self._collapse(edges)
        submitted = self._collapse(self.submitted_edges)

        correct_edges = [edges for pair, edges in truth.items() if pair in submitted]
        missing_edges = [
            edges for pair, edges in truth.items() if pair not in submitted
        ]
        additional_edges = [
            edges for pair, edges in submitted.items() if pair not in truth
        ]

        return (correct_edges, missing_edges, additional_edges)

    @staticmethod
    def _collapse(edges: list[dict]) -> dict[tuple[str, str], list[dict]]:
        pairs = {}
        for edge in edges:
            pairs.setdefault((edge["caller"], edge["callee"]), []).append(edge)
        return pairs

    def _score_extended(self, nodes: list[dict], edges: list[dict]):
        # TODO: compare result to ground truth
        # TODO: score with modifiers
        raise NotImplementedError()

    def score(self, dbs: bool, async_edges: bool, extended: bool) -> dict:
        if self.nodes is None:
            raise PipelineException("Scoring without loaded data")

        nodes, edges = self.nodes, self.edges
        if not dbs:
            nodes = [x for x in nodes if x["kind"] != "datastore"]
            edges = [x for x in edges if x["type"] != "query"]

        if async_edges:
            raise NotImplementedError()
        else:
            pass  # TODO

        if extended:
            correct, missing, additional = self._score_extended(nodes, edges)
        else:
            correct, missing, additional = self._score_base(nodes, edges)

        # TODO: more detailed statistics (per pattern scoring...)
        return {
            "version": self.dataset_version,
            "correct": len(correct),
            "missing": len(missing),
            "additional": len(additional),
        }


def main():
    source_dir = Path(__file__).resolve().parent.parent.parent
    expected_connections = f"{source_dir}/dataset/connections.json"

    parser = argparse.ArgumentParser(description="The PolyEats result grading utility")
    parser.add_argument("results_file")
    parser.add_argument(
        "--ground-truth", dest="ground_truth", default=expected_connections
    )
    parser.add_argument("--dbs", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument(
        "--async",
        dest="async_edges",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    parser.add_argument(
        "--extended", action=argparse.BooleanOptionalAction, default=False
    )

    arguments = parser.parse_args()

    grader = Grader(arguments.ground_truth)
    try:
        grader.load(arguments.results_file)
    except (
        OSError,
        json.JSONDecodeError,
        SchemaException,
        SubmissionException,
        NotImplementedError
    ) as error:
        sys.exit(f"error: {error}")
    result = grader.score(arguments.dbs, arguments.async_edges, arguments.extended)

    print(json.dumps(result))


if __name__ == "__main__":
    main()
