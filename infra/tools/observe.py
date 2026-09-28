import argparse
import json
import re
import sys

import canonicalise
from schema_constants import Constants

SERVER, CLIENT = 2, 3
SUPPORTED_TYPES = {"rest", "grpc", "query"}
TABLE = re.compile(r"\b(?:FROM|INTO|UPDATE|JOIN)\s+([\w.]+)", re.IGNORECASE)


def attributes(item):
    return {
        attribute["key"]: next(iter(attribute["value"].values()), None)
        for attribute in item.get("attributes", [])
    }


def spans(path):
    with open(path) as source:
        for line in source:
            if not line.strip():
                continue
            for resource_spans in json.loads(line).get("resourceSpans", []):
                service = attributes(resource_spans.get("resource", {})).get(
                    "service.name"
                )
                for scope_spans in resource_spans.get("scopeSpans", []):
                    for span in scope_spans.get("spans", []):
                        yield {
                            "key": (span["traceId"], span["spanId"]),
                            "parent": (span["traceId"], span.get("parentSpanId", "")),
                            "service": service,
                            "kind": span.get("kind"),
                            "name": span["name"],
                            "attributes": attributes(span),
                        }


def endpoint(server):
    attrs = server["attributes"]
    if "rpc.method" in attrs:
        method = attrs["rpc.method"]
        full = method if "/" in method else f"{attrs.get('rpc.service')}/{method}"
        service, method = full.lstrip("/").split("/")
        return f"{service.rsplit('.', 1)[-1]}/{method}"
    if attrs.get("http.route"):
        method = attrs.get("http.request.method") or attrs.get("http.method")
        return f"{method} {attrs['http.route']}"
    return server["name"]


def enclosing_server(span, by_key):
    while span is not None and span["kind"] != SERVER:
        parent = by_key.get(span["parent"])
        span = parent if parent and parent["service"] == span["service"] else None
    return span


def table(attrs):
    name = attrs.get("db.collection.name") or attrs.get("db.sql.table")
    if name:
        return name
    match = TABLE.search(attrs.get("db.query.text") or attrs.get("db.statement") or "")
    return match and match.group(1)


def callee(client, servers):
    attrs = client["attributes"]
    if "db.system" in attrs or "db.system.name" in attrs:
        name = table(attrs)
        # Every service owns its datastore, and sqlite spans carry no database name.
        return name and ("query", f"db:{client['service']}", name)

    server = servers.get(client["key"])
    if server is None:
        return None
    edge_type = "grpc" if "rpc.method" in attrs else "rest"
    return edge_type, server["service"], endpoint(server)


def observed_edges(path, kinds):
    collected = list(spans(path))
    by_key = {span["key"]: span for span in collected}
    servers = {span["parent"]: span for span in collected if span["kind"] == SERVER}

    edges = {}
    undeclared = set()
    for client in collected:
        if client["kind"] != CLIENT:
            continue
        target = callee(client, servers)
        server = enclosing_server(client, by_key)
        if target is None or server is None:
            continue

        edge_type, callee_node, callee_endpoint = target
        undeclared |= {client["service"], callee_node} - kinds.keys()

        edge = dict.fromkeys(Constants.EDGE_KEYS)
        edge |= {
            "caller": client["service"],
            "caller_endpoint": endpoint(server),
            "callee": callee_node,
            "callee_endpoint": callee_endpoint,
            "type": edge_type,
            "static": False,
            "observed": True,
        }
        edge["id"] = canonicalise.Formatter.edge_id(edge)
        edges[edge["id"]] = edge

    if undeclared:
        sys.exit(f"undeclared nodes observed: {sorted(undeclared)}")
    return edges


def main():
    parser = argparse.ArgumentParser(
        description="mark connections.json edges observed from the collector's OTLP JSON trace export"
    )
    parser.add_argument("traces")
    parser.add_argument("connections")
    arguments = parser.parse_args()

    with open(arguments.connections) as source:
        data = json.load(source)

    unsupported = {edge["type"] for edge in data["edges"]} - SUPPORTED_TYPES
    if unsupported:
        sys.exit(f"observed scan does not support edge types {sorted(unsupported)}")

    kinds = {node["id"]: node["kind"] for node in data["nodes"]}
    observed = observed_edges(arguments.traces, kinds)
    if not observed:
        sys.exit("no edges observed")

    declared = {edge["id"] for edge in data["edges"]}
    for edge in data["edges"]:
        edge["observed"] = edge["id"] in observed
    data["edges"] = [
        edge for edge in data["edges"] if edge["static"] or edge["observed"]
    ]
    data["edges"] += [
        edge for edge_id, edge in observed.items() if edge_id not in declared
    ]

    formatter = canonicalise.Formatter(data)
    formatter.validate()
    formatter.report()
    with open(arguments.connections, "w") as destination:
        destination.write(formatter.serialise())

    for edge in data["edges"]:
        if not edge["observed"]:
            print(f"static only:  {edge['id']}")
        elif not edge["static"]:
            print(f"runtime only: {edge['id']}")
    print(f"{len(observed)} edges observed")


if __name__ == "__main__":
    main()
