import argparse
import json


def spans(path):
    with open(path) as source:
        for line in source:
            if not line.strip():
                continue
            for resource_spans in json.loads(line).get("resourceSpans", []):
                for scope_spans in resource_spans.get("scopeSpans", []):
                    yield from scope_spans.get("spans", [])


def main():
    parser = argparse.ArgumentParser(
        description="read the collector's OTLP JSON trace export"
    )
    parser.add_argument("path")
    arguments = parser.parse_args()

    print(f"{sum(1 for _ in spans(arguments.path))} spans")


if __name__ == "__main__":
    main()
