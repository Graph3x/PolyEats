import argparse
import json
import sys
from datetime import datetime, timezone

import canonicalise
from schema_constants import Constants


def main():
    parser = argparse.ArgumentParser(
        description="stamp release metadata onto a canonical baseline"
    )
    parser.add_argument("path")
    parser.add_argument("--dataset-version", required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument(
        "--doi", help="only archived releases are deposited and get one"
    )
    parser.add_argument("-o", "--output")
    arguments = parser.parse_args()

    with open(arguments.path) as source:
        data = json.load(source)

    data["dataset_version"] = arguments.dataset_version
    data["timestamp"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    data["source"] = {"repo": arguments.repo, "commit": arguments.commit}
    data["doi"] = arguments.doi

    formatter = canonicalise.Formatter(data)

    formatter.validate()
    formatter.errors += [
        f"top level: {key!r} must not be null in a release"
        for key in Constants.RELEASE_REQUIRED
        if not data.get(key)
    ]
    if formatter.errors:
        formatter.report()

    formatter.complete()
    formatter.check_references()
    if formatter.errors:
        formatter.report()

    output = formatter.serialise()
    if arguments.output:
        with open(arguments.output, "w") as destination:
            destination.write(output)
        print(f"{arguments.output} written", file=sys.stderr)
    else:
        sys.stdout.write(output)


if __name__ == "__main__":
    main()
