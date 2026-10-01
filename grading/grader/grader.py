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
            submission = json.loads(f.read())

        with open(self.dataset, "r") as f:
            truth = json.loads(f.read())

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
                """You have a node mismatch - this generally shouldnt happen.
                Please check that you are using a correct adapter and that 
                your naming convention matches the folder names"""
            )

        correct_edges = []
        missing_edges = []
        additional_edges = []

        for edge in self.edges:
            for candidate in self.submitted_edges:
                if (
                    edge["caller"] == candidate["caller"]
                    and edge["callee"] == candidate["callee"]
                ):
                    correct_edges.append(edge)
                    break
            else:
                missing_edges.append(edge)

        for edge in self.submitted_edges:
            for candidate in self.edges:
                if (
                    edge["caller"] == candidate["caller"]
                    and edge["callee"] == candidate["callee"]
                ):
                    break
            else:
                additional_edges.append(edge)

        return (correct_edges, missing_edges, additional_edges)

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
