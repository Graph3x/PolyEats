import argparse
import json
import re
from pathlib import Path

LITERAL = re.compile(r"\w+://([\w-]+)|\b([\w-]+):\d+")


def find_edges(root: Path, services: set[str]) -> set[tuple[str, str]]:
    edges = set()
    for caller in services:
        for file in (root / caller).rglob("*"):
            if not file.is_file():
                continue
            for match in LITERAL.finditer(file.read_text(errors="ignore")):
                callee = match.group(1) or match.group(2)
                if callee in services and callee != caller:
                    edges.add((caller, callee))
    return edges


def main():
    parser = argparse.ArgumentParser(
        description="naive baseline: grep each service's own files for URL and host:port literals naming another service"
    )
    parser.add_argument("services")
    parser.add_argument("--output", required=False)
    arguments = parser.parse_args()

    root = Path(arguments.services)
    services = {path.name for path in root.iterdir() if path.is_dir()}
    edges = find_edges(root, services)

    result = json.dumps(
        {
            "nodes": sorted(services),
            "edges": [
                {"caller": caller, "callee": callee} for caller, callee in sorted(edges)
            ],
        },
        indent=2,
    )

    if arguments.output:
        with open(arguments.output, "w") as f:
            f.write(result)
        return

    print(result)
        

if __name__ == "__main__":
    main()
