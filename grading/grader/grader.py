import argparse
import json
from pathlib import Path

VERSION = "1.1.1"


class SchemaException(Exception):
    pass


class PipelineException(Exception):
    pass


class Grader:
    def __init__(self, dataset_path: str):
        self.dataset = dataset_path
        self.nodes = None
        self.edges = None

    def load(self, submission_path: str, adapter: str | None) -> None:
        with open(submission_path, "r") as f:
            submission = json.load(f)

        with open(self.dataset, "r") as f:
            truth = json.load(f)

        if truth.get("schema_version", "") != VERSION:
            raise SchemaException("Dataset schema doesnt match grader!")

        self.dataset_version = truth["dataset_version"]
        self.nodes = truth["nodes"]
        self.edges = truth["edges"]

        if adapter:
            # TODO: apply adapter
            pass

        self.submitted_nodes = submission["nodes"]
        self.submitted_edges = submission["edges"]

    def _score_base(self):

        if {x["id"] for x in self.nodes} != set(self.submitted_nodes):
            print(
                "You have a node mismatch - this generally shouldnt happen.\n"
                "Please check that you are using a correct adapter and that "
                "your naming convention matches the folder names"
            )

        truth = self._collapse(self.edges)
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

    def _score_extended(self):
        # TODO: compare result to ground truth
        # TODO: score with modifiers
        return ([], [], [])

    def score(self, dbs: bool, broker: bool, extended: bool) -> dict:
        if self.nodes is None:
            raise PipelineException("Scoring without loaded data")

        if not dbs:
            self.nodes = [x for x in self.nodes if x["kind"] != "datastore"]
            self.edges = [x for x in self.edges if x["type"] != "query"]

        if not broker:
            pass  # TODO

        if extended:
            correct, missing, additional = self._score_extended()
        else:
            correct, missing, additional = self._score_base()

        # TODO: more detailed statistics
        return {
            "correct": len(correct),
            "missing": len(missing),
            "additional": len(additional),
        }


def main():
    source_dir = Path(__file__).resolve().parent.parent.parent
    expected_connections = f"{source_dir}/dataset/connections.json"

    parser = argparse.ArgumentParser(description="The PolyEats result grading utility")
    parser.add_argument("results_file")
    parser.add_argument("--adapter", required=False)
    parser.add_argument("--ground_truth", default=expected_connections)
    parser.add_argument("--dbs", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument("--broker", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument(
        "--extended", action=argparse.BooleanOptionalAction, default=False
    )

    arguments = parser.parse_args()

    grader = Grader(arguments.ground_truth)
    grader.load(arguments.results_file, arguments.adapter)
    result = grader.score(arguments.dbs, arguments.broker, arguments.extended)

    print(result)


if __name__ == "__main__":
    main()
