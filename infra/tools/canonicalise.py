import argparse
import hashlib
import json
import sys

UNIT_SEPARATOR = "\x1f"

TOP_KEYS = ["schema_version", "dataset_version", "timestamp", "source",
            "license", "doi", "nodes", "edges"]
SOURCE_KEYS = ["repo", "commit"]
NODE_KEYS = ["id", "kind", "language", "stack", "broker",
             "native_kind", "native_name", "routing", "delivery"]
EDGE_KEYS = ["id", "caller", "caller_endpoint", "callee", "callee_endpoint", "type",
             "pattern", "routing_key", "headers", "selector", "role",
             "derived_from", "static", "observed"]

RELEASE_ONLY = ["dataset_version", "timestamp", "source", "doi"]

KINDS = {"service", "datastore", "destination", "external", "client", "broker"}
LANGUAGES = {"go", "java", "python"}
NATIVE_KINDS = {"exchange", "queue", "topic", "subject", "subscription",
                "consumer-group", "stream"}
ROUTINGS = {"exact", "pattern", "broadcast", "headers", "hash", "none"}
DELIVERIES = {"competing", "broadcast"}
TYPES = {"rest", "grpc", "grpc-stream", "websocket", "async", "async-derived", "query"}
ROLES = {"primary", "alternate", "dead-letter"}
PATTERNS = {"literal-url", "string-concatenation", "env-var-config",
            "cross-file-constant", "class-field-default", "client-wrapper",
            "conditional-branch", "closure-captured", "gateway-indirection",
            "service-discovery-lookup"}
PATTERN_TYPES = {"rest", "grpc", "grpc-stream"}


def _enum(errors, where, value, allowed):
    if value is not None and value not in allowed:
        errors.append(f"{where}: {value!r} not one of {sorted(allowed)}")


def _validate_metadata(data):
    errors = []
    for key in TOP_KEYS:
        if key not in data:
            errors.append(f"top level: missing {key!r}")
    for key in ("schema_version", "license"):
        if data.get(key) is None:
            errors.append(f"top level: {key!r} must not be null")

    source = data.get("source")
    if source is not None:
        for key in SOURCE_KEYS:
            if not source.get(key):
                errors.append(f"source: missing {key!r}")
    return errors


def _validate_nodes(nodes):
    errors = []
    seen = set()
    for index, node in enumerate(nodes):
        for key in NODE_KEYS:
            if key not in node:
                errors.append(f"node[{index}]: missing {key!r}")

        node_id = node.get("id")
        if not node_id:
            errors.append(f"node[{index}]: 'id' must not be empty")
            continue

        where = f"node {node_id!r}"
        if node_id in seen:
            errors.append(f"{where}: duplicate id")
        seen.add(node_id)

        _enum(errors, where, node.get("kind"), KINDS)
        _enum(errors, where, node.get("language"), LANGUAGES)
        _enum(errors, where, node.get("native_kind"), NATIVE_KINDS)
        _enum(errors, where, node.get("routing"), ROUTINGS)
        _enum(errors, where, node.get("delivery"), DELIVERIES)
    return errors


def _validate_edges(edges, kinds):
    errors = []
    for index, edge in enumerate(edges):
        where = f"edge[{index}] {edge.get('caller')!r}->{edge.get('callee')!r}"
        edge_type = edge.get("type")

        for key in EDGE_KEYS:
            if key != "id" and key not in edge:
                errors.append(f"{where}: missing {key!r}")
        for end in ("caller", "callee"):
            if edge.get(end) not in kinds:
                errors.append(f"{where}: {end} {edge.get(end)!r} is not a declared node")

        _enum(errors, where, edge_type, TYPES)
        _enum(errors, where, edge.get("role"), ROLES)

        patterns = edge.get("pattern")
        if patterns is not None:
            if edge_type not in PATTERN_TYPES:
                errors.append(f"{where}: 'pattern' only applies to {sorted(PATTERN_TYPES)}")
            for pattern in patterns:
                _enum(errors, where, pattern, PATTERNS)

        if edge_type == "query" and kinds.get(edge.get("callee")) != "datastore":
            errors.append(f"{where}: 'query' edges must end at a datastore")
        if edge_type == "async" and "destination" not in (
                kinds.get(edge.get("caller")), kinds.get(edge.get("callee"))):
            errors.append(f"{where}: 'async' edges need a destination at one or both ends")
        if edge.get("derived_from") is not None and edge_type != "async-derived":
            errors.append(f"{where}: 'derived_from' only applies to 'async-derived'")

        for key in ("static", "observed"):
            if not isinstance(edge.get(key), bool):
                errors.append(f"{where}: {key!r} must be a boolean")
        if edge.get("static") is False and edge.get("observed") is False:
            errors.append(f"{where}: at least one of 'static' and 'observed' must be true")
    return errors


def validate(data):
    errors = _validate_metadata(data)

    nodes, edges = data.get("nodes"), data.get("edges")
    if not isinstance(nodes, list) or not isinstance(edges, list):
        return errors + ["top level: 'nodes' and 'edges' must both be arrays"]

    kinds = {node["id"]: node.get("kind") for node in nodes if node.get("id")}
    return errors + _validate_nodes(nodes) + _validate_edges(edges, kinds)


def validate_edge_ends(data):
    errors = []
    for index, edge in enumerate(data.get("edges") or []):
        for end in ("caller", "callee"):
            if not edge.get(end):
                errors.append(f"edge[{index}]: missing {end!r}")
    return errors


def check_references(data):
    known = {edge["id"] for edge in data["edges"]}
    errors = []
    for edge in data["edges"]:
        for reference in edge.get("derived_from") or []:
            if reference not in known:
                errors.append(f"edge {edge['id']!r}: derived_from {reference!r} does not exist")
    return errors


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


def complete(data):
    for edge in data["edges"]:
        edge["id"] = edge_id(edge)


def _ordered(item, keys):
    return {key: item.get(key) for key in keys}


def serialise(data):
    canonical = _ordered(data, TOP_KEYS)
    if canonical.get("source") is not None:
        canonical["source"] = _ordered(canonical["source"], SOURCE_KEYS)
    canonical["nodes"] = [_ordered(node, NODE_KEYS)
                          for node in sorted(data["nodes"], key=lambda node: node["id"])]
    canonical["edges"] = [_ordered(edge, EDGE_KEYS)
                          for edge in sorted(data["edges"], key=lambda edge: edge["id"])]
    return json.dumps(canonical, indent=2) + "\n"


def report(errors):
    if not errors:
        return
    for error in errors:
        print(error, file=sys.stderr)
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="canonicalise a connections.json baseline")
    parser.add_argument("path")
    parser.add_argument("--check", action="store_true",
                        help="verify instead of writing")
    parser.add_argument("--ids-only", action="store_true",
                        help="recompute edge ids only, leaving order and layout untouched")
    arguments = parser.parse_args()

    with open(arguments.path) as source:
        original = source.read()
    data = json.loads(original)

    if arguments.ids_only:
        report(validate_edge_ends(data))
        complete(data)
        output = json.dumps(data, indent=2) + "\n"
    else:
        report(validate(data))
        complete(data)
        report(check_references(data))
        output = serialise(data)

    if arguments.check:
        if output != original:
            print(f"{arguments.path} is out of date; rerun without --check", file=sys.stderr)
            sys.exit(1)
        print(f"{arguments.path} ok")
        return

    with open(arguments.path, "w") as destination:
        destination.write(output)
    print(f"{arguments.path} written")


if __name__ == "__main__":
    main()
