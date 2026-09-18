import hashlib
import json
from pathlib import Path

import pytest
from canonicalise import Formatter
from schema_constants import Constants

BASELINE = Path(__file__).resolve().parents[2] / "dataset" / "connections.json"


def node(**fields):
    return {key: fields.get(key) for key in Constants.NODE_KEYS}


def edge(**fields):
    built = {key: fields.get(key) for key in Constants.EDGE_KEYS}
    built["static"] = fields.get("static", True)
    built["observed"] = fields.get("observed", False)
    return built


def document(nodes=None, edges=None):
    return {
        "schema_version": "1.1.1",
        "dataset_version": None,
        "timestamp": None,
        "source": None,
        "license": "Apache-2.0",
        "doi": None,
        "nodes": nodes
        if nodes is not None
        else [
            node(id="svc", kind="service", language="go", stack="grpc-go"),
            node(id="db:store", kind="datastore", stack="sqlite-ro"),
        ],
        "edges": edges
        if edges is not None
        else [
            edge(
                caller="svc",
                caller_endpoint="Svc/Get",
                callee="db:store",
                callee_endpoint="rows",
                type="query",
            ),
        ],
    }


def errors_for(data):
    formatter = Formatter(data)
    formatter.validate()
    return " ".join(formatter.errors)


# --check compares the tool's output against a file the same tool produced, so a
# wrong hash verifies clean. Only an independent digest catches that.
def test_hash_matches_independently_computed_digest():
    subject = {"caller_endpoint": "GET /x", "callee_endpoint": "S/M"}
    expected = hashlib.sha256(b"GET /x\x1fS/M\x1f\x1f\x1f\x1f").hexdigest()[:6]
    assert Formatter({}).hash6(subject) == expected


def test_absent_field_equals_explicit_null():
    formatter = Formatter({})
    sparse = {"caller_endpoint": "GET /x"}
    explicit = {
        "caller_endpoint": "GET /x",
        "routing_key": None,
        "headers": None,
        "selector": None,
        "role": None,
    }
    assert formatter.hash6(sparse) == formatter.hash6(explicit)


def test_only_selector_expression_participates():
    formatter = Formatter({})
    pattern = {
        "selector": {"type": "pattern", "syntax": "amqp-topic", "expression": "order.*"}
    }
    exact = {"selector": {"type": "exact", "expression": "order.*"}}
    assert formatter.hash6(pattern) == formatter.hash6(exact)
    assert formatter.hash6(pattern) != formatter.hash6({})


def test_edge_id_is_caller_callee_hash():
    formatter = Formatter({})
    subject = {"caller": "a", "callee": "db:x"}
    assert formatter.edge_id(subject) == f"a.db:x.{formatter.hash6(subject)}"


def test_serialise_orders_keys_sorts_nodes_and_ends_with_newline():
    data = document(
        nodes=[node(id="zeta", kind="service"), node(id="alpha", kind="service")],
        edges=[],
    )
    output = Formatter(data).serialise()
    parsed = json.loads(output)

    assert list(parsed) == Constants.TOP_KEYS
    assert list(parsed["nodes"][0]) == Constants.NODE_KEYS
    assert [n["id"] for n in parsed["nodes"]] == ["alpha", "zeta"]
    assert output.endswith("}\n")


def test_serialise_is_idempotent():
    formatter = Formatter(document())
    formatter.complete()
    once = formatter.serialise()

    again = Formatter(json.loads(once))
    again.complete()
    assert again.serialise() == once


def test_minimal_document_is_valid():
    assert errors_for(document()) == ""


@pytest.mark.parametrize(
    "mutate, expected",
    [
        (lambda d: d["edges"][0].update(callee="ghost"), "is not a declared node"),
        (lambda d: d["nodes"].append(dict(d["nodes"][0])), "duplicate id"),
        (lambda d: d["nodes"][0].update(language="rust"), "not one of"),
        (lambda d: d["edges"][0].update(callee="svc"), "must end at a datastore"),
        (
            lambda d: d["edges"][0].update(pattern=["literal-url"]),
            "'pattern' only applies to",
        ),
        (lambda d: d["edges"][0].update(static=False), "at least one of"),
        (
            lambda d: d["edges"][0].update(derived_from=["nope"]),
            "only applies to 'async-derived'",
        ),
        (lambda d: d.update(nodes=None), "must both be arrays"),
        (lambda d: d.pop("license"), "missing 'license'"),
    ],
)
def test_validation_rule_fires(mutate, expected):
    data = document()
    mutate(data)
    assert expected in errors_for(data)


def test_committed_baseline_is_valid_and_canonical():
    original = BASELINE.read_text()
    formatter = Formatter(json.loads(original))

    formatter.validate()
    formatter.complete()
    formatter.check_references()

    assert formatter.errors == []
    assert formatter.serialise() == original
