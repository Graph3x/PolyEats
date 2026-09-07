import argparse
import json
import sys
from datetime import datetime, timezone

import canonicalise


# This is a quick AI draft not ment for use.
# I will come back to refactor this later,
# this file should server as reference only,
def main():
    parser = argparse.ArgumentParser(description="stamp release metadata onto a canonical baseline")
    parser.add_argument("path")
    parser.add_argument("--dataset-version", required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--doi", required=True)
    parser.add_argument("-o", "--output")
    arguments = parser.parse_args()

    with open(arguments.path) as source:
        data = json.load(source)

    data["dataset_version"] = arguments.dataset_version
    data["timestamp"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    data["source"] = {"repo": arguments.repo, "commit": arguments.commit}
    data["doi"] = arguments.doi

    errors = canonicalise.validate(data)
    errors += [f"top level: {key!r} must not be null in a release"
               for key in canonicalise.RELEASE_ONLY if not data.get(key)]
    if errors:
        canonicalise.report(errors)

    canonicalise.complete(data)
    errors = canonicalise.check_references(data)
    if errors:
        canonicalise.report(errors)

    output = canonicalise.serialise(data)
    if arguments.output:
        with open(arguments.output, "w") as destination:
            destination.write(output)
        print(f"{arguments.output} written", file=sys.stderr)
    else:
        sys.stdout.write(output)


if __name__ == "__main__":
    main()
