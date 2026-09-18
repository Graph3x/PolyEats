import argparse
import hashlib
import json
import sys
from typing import Any

from schema_constants import Constants


class Formatter:
    def __init__(self, data: dict[str, Any]) -> None:

        self.errors: list[str] = []
        self.data = data

    def _validate_metadata(self) -> None:
        for key in Constants.TOP_KEYS:
            if key not in self.data:
                self.errors.append(f"top level: missing {key!r}")
        for key in ("schema_version", "license"):
            if self.data.get(key) is None:
                self.errors.append(f"top level: {key!r} must not be null")

        source = self.data.get("source")
        if source is not None:
            for key in Constants.SOURCE_KEYS:
                if not source.get(key):
                    self.errors.append(f"source: missing {key!r}")

    def _enum(self, where, value, allowed) -> None:
        if value is not None and value not in allowed:
            self.errors.append(f"{where}: {value!r} not one of {sorted(allowed)}")

    def _validate_nodes(self, nodes: list) -> None:
        seen = set()
        for index, node in enumerate(nodes):
            for key in Constants.NODE_KEYS:
                if key not in node:
                    self.errors.append(f"node[{index}]: missing {key!r}")

            node_id = node.get("id")
            if not node_id:
                self.errors.append(f"node[{index}]: 'id' must not be empty")
                continue

            where = f"node {node_id!r}"
            if node_id in seen:
                self.errors.append(f"{where}: duplicate id")
            seen.add(node_id)

            self._enum(where, node.get("kind"), Constants.KINDS)
            self._enum(where, node.get("language"), Constants.LANGUAGES)
            self._enum(where, node.get("native_kind"), Constants.NATIVE_KINDS)
            self._enum(where, node.get("routing"), Constants.ROUTINGS)
            self._enum(where, node.get("delivery"), Constants.DELIVERIES)

    def _validate_edges(self, edges: list, kinds: dict) -> None:
        for index, edge in enumerate(edges):
            where = f"edge[{index}] {edge.get('caller')!r}->{edge.get('callee')!r}"
            edge_type = edge.get("type")

            for key in Constants.EDGE_KEYS:
                if key != "id" and key not in edge:
                    self.errors.append(f"{where}: missing {key!r}")
            for end in ("caller", "callee"):
                if edge.get(end) not in kinds:
                    self.errors.append(
                        f"{where}: {end} {edge.get(end)!r} is not a declared node"
                    )

            self._enum(where, edge_type, Constants.TYPES)
            self._enum(where, edge.get("role"), Constants.ROLES)

            patterns = edge.get("pattern")
            if patterns is not None:
                if edge_type not in Constants.PATTERN_TYPES:
                    self.errors.append(
                        f"{where}: 'pattern' only applies to {sorted(Constants.PATTERN_TYPES)}"
                    )
                for pattern in patterns:
                    self._enum(where, pattern, Constants.PATTERNS)

            if edge_type == "query" and kinds.get(edge.get("callee")) != "datastore":
                self.errors.append(f"{where}: 'query' edges must end at a datastore")
            if edge_type == "async" and "destination" not in (
                kinds.get(edge.get("caller")),
                kinds.get(edge.get("callee")),
            ):
                self.errors.append(
                    f"{where}: 'async' edges need a destination at one or both ends"
                )
            if edge.get("derived_from") is not None and edge_type != "async-derived":
                self.errors.append(
                    f"{where}: 'derived_from' only applies to 'async-derived'"
                )

            for key in ("static", "observed"):
                if not isinstance(edge.get(key), bool):
                    self.errors.append(f"{where}: {key!r} must be a boolean")
            if edge.get("static") is False and edge.get("observed") is False:
                self.errors.append(
                    f"{where}: at least one of 'static' and 'observed' must be true"
                )

    @staticmethod
    def _ordered(item, keys):
        return {key: item.get(key) for key in keys}

    def validate(self) -> None:
        self._validate_metadata()

        nodes, edges = self.data.get("nodes"), self.data.get("edges")
        if not isinstance(nodes, list) or not isinstance(edges, list):
            self.errors.append("top level: 'nodes' and 'edges' must both be arrays")
            return

        kinds = {node["id"]: node.get("kind") for node in nodes if node.get("id")}

        self._validate_nodes(nodes)
        self._validate_edges(edges, kinds)

    def validate_edge_ends(self) -> None:
        for index, edge in enumerate(self.data["edges"]):
            for end in ("caller", "callee"):
                if not edge.get(end):
                    self.errors.append(f"edge[{index}]: missing {end!r}")

    def complete(self) -> None:
        for edge in self.data["edges"]:
            edge["id"] = Formatter.edge_id(edge)

    def report(self) -> None:
        if not self.errors:
            return
        for error in self.errors:
            print(error, file=sys.stderr)
        sys.exit(1)

    def check_references(self):
        known = {edge["id"] for edge in self.data["edges"]}
        for edge in self.data["edges"]:
            for reference in edge.get("derived_from") or []:
                if reference not in known:
                    self.errors.append(
                        f"edge {edge['id']!r}: derived_from {reference!r} does not exist"
                    )

    @staticmethod
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
        joined = Constants.SEPARATOR.join(
            "" if field is None else field for field in fields
        )
        return hashlib.sha256(joined.encode("utf-8")).hexdigest()[:6]

    @staticmethod
    def edge_id(edge):
        return f"{edge['caller']}.{edge['callee']}.{Formatter.hash6(edge)}"

    def serialise(self):
        canonical = Formatter._ordered(self.data, Constants.TOP_KEYS)
        if canonical.get("source") is not None:
            canonical["source"] = Formatter._ordered(
                canonical["source"], Constants.SOURCE_KEYS
            )
        canonical["nodes"] = [
            Formatter._ordered(node, Constants.NODE_KEYS)
            for node in sorted(self.data["nodes"], key=lambda node: node["id"])
        ]
        for edge in self.data["edges"]:
            if edge.get("pattern") is not None:
                edge["pattern"] = sorted(edge["pattern"])
        canonical["edges"] = [
            Formatter._ordered(edge, Constants.EDGE_KEYS)
            for edge in sorted(self.data["edges"], key=lambda edge: edge["id"])
        ]
        return json.dumps(canonical, indent=2) + "\n"


def main():
    parser = argparse.ArgumentParser(
        description="canonicalise a connections.json baseline"
    )
    parser.add_argument("path")
    parser.add_argument(
        "--check", action="store_true", help="verify instead of writing"
    )
    parser.add_argument(
        "--ids-only",
        action="store_true",
        help="recompute edge ids only, leaving order and layout untouched",
    )
    arguments = parser.parse_args()

    with open(arguments.path) as source:
        original = source.read()
    data = json.loads(original)

    formatter = Formatter(data)

    if arguments.ids_only:
        formatter.validate_edge_ends()
        formatter.report()

        formatter.complete()
        output = json.dumps(formatter.data, indent=2) + "\n"

    else:
        formatter.validate()
        formatter.report()
        formatter.complete()

        formatter.check_references()
        formatter.report()
        output = formatter.serialise()

    if arguments.check:
        if output != original:
            print(
                f"{arguments.path} is not canonical",
                file=sys.stderr,
            )
            sys.exit(1)
        print(f"{arguments.path} ok")
        return

    with open(arguments.path, "w") as destination:
        destination.write(output)
    print(f"{arguments.path} written")


if __name__ == "__main__":
    main()
