import hashlib
import json
import sys

UNIT_SEPARATOR = "\x1f"


def hash6(edge):
    selector = edge.get("selector") or {}
    fields = [
        edge.get("caller_endpoint"),
        edge.get("callee_endpoint"),
        edge.get("routing_key"),
        edge.get("headers"),
        selector.get("expression"),
        edge.get("role"),
    ]
    joined = UNIT_SEPARATOR.join("" if field is None else field for field in fields)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()[:6]


def edge_id(edge):
    return f"{edge['caller']}.{edge['callee']}.{hash6(edge)}"


def main():
    if len(sys.argv) > 1:
        with open(sys.argv[1]) as source:
            data = json.load(source)
    else:
        data = json.load(sys.stdin)

    for edge in data if isinstance(data, list) else [data]:
        print(edge_id(edge))


if __name__ == "__main__":
    main()
