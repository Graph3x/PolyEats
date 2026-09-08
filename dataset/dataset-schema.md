# PolyEats - dataset schema version 1.1.0

Specification for the published dataset: file layout, node/edge schema, enums, and serialization rules.

---

## File layout

| File | Contents |
|---|---|
| `connections.json` | The dataset itself (nodes and edges) |
| `validation-report.json` | Cohen's κ · how the rated sample was picked · who rated it |


---

## `connections.json` - top level

| Field | Type | Required | Notes |
|---|---|---|---|
| `schema_version` | string | yes | semver of this schema |
| `dataset_version` | string | yes (on release) | semver of this release |
| `timestamp` | iso timestamp (utc) | yes (on release) | |
| `source` | object | yes (on release) | `{repo, commit}` |
| `license` | string | yes | SPDX id — `Apache-2.0` |
| `doi` | string | yes (on release) | Reserved on Zenodo *before* the release is generated, so the frozen artifact is self-describing |
| `nodes` | array | yes | |
| `edges` | array | yes | |

---

## Interpretation

**Async span topology: links.** Consumers link to the producer's publish span rather than inheriting its trace; async edges are recovered from span attributes, not from link traversal.

**Instance normalization.** Replica identity is stripped from traces, a node is a service, never one instance of it.

**Derived edges.** There is always at most a single async-derived edge between two services in each direction - no matter how many different async edges it could be derived from.

---

## Nodes

| Field | Type | Relevant for | Notes |
|---|---|---|---|
| `id` | string | all | see [Node ids](#node-ids) |
| `kind` | enum | all | |
| `language` | enum \| null | `service` | |
| `stack` | string \| null | `service`, `datastore`, `broker` | |
| `broker` | string \| null | `destination` | node id of the hosting broker |
| `native_kind` | enum \| null | `destination` | broker's own term |
| `native_name` | string \| null | `destination` | name in the broker |
| `routing` | enum \| null | `destination` | selection toward other destinations |
| `delivery` | enum \| null | `destination` | dispatch toward consumers |

### Enums

```
kind         service · datastore · destination · external · client · broker
language     go · java · python
native_kind  exchange · queue · topic · subject · subscription ·
             consumer-group · stream
routing      exact · pattern · broadcast · headers · hash · none
delivery     competing · broadcast
```

`stack` is open: service frameworks (`flask`, `fastapi`, `spring-boot`, `grpc-go` ...), datastore engines (`postgres`, `mongodb`, `valkey`,
`sqlite`, `sqlite-ro`), brokers (`rabbitmq`). Name only, no version.

`client` and `external` are both outside the system; they differ in what is
recoverable. An `external` target is resolved by source in the repo (a
`PSP_URL` in config), a `client` is not.

### Node ids

| kind | Form |
|---|---|
| `service`, `client`, `external`, `broker` | bare name, for example `order-state` |
| `datastore` | `db:<name>` |
| `destination` | `dest:<name>` |

Bare names share one namespace and must be globally unique across the four
kinds that use them.

### Communication edges by kind

`broker` nodes carry **no** edges, they are only referenced by `destination.broker`. All other kinds carry edges.

---

## Edges

| Field | Type | Relevant for | Notes |
|---|---|---|---|
| `id` | string | all | see [Edge ids](#edge-ids) |
| `caller` | string | all | node id |
| `caller_endpoint` | string \| null | all | endpoint the call originates from |
| `callee` | string | all | node id |
| `callee_endpoint` | string \| null | all but destination-targeting | endpoint, or table/collection for `query` |
| `type` | enum | all | |
| `pattern` | enum array \| null | `rest`, `grpc`, `grpc-stream` | |
| `routing_key` | string \| null | `async` service→destination | |
| `headers` | string \| null | `async` service→destination | routing-relevant headers, same form as a `headers` selector |
| `selector` | object \| null | `async` destination→destination | see [Selectors](#selectors) |
| `role` | enum \| null | `async` destination→destination | |
| `derived_from` | array \| null | `async-derived` | constituent edge ids |
| `static` | bool | all | resolvable from source |
| `observed` | bool | all | fired in this release's reference run |

At least one of `static` and `observed` is always true.


### Enums

```
type      rest · grpc · grpc-stream · websocket ·
          async · async-derived · query
role      primary · alternate · dead-letter

pattern   literal-url · string-concatenation · env-var-config ·
          cross-file-constant · class-field-default · client-wrapper ·
          conditional-branch · closure-captured · gateway-indirection
          reserved: service-discovery-lookup
```

Some `type`s constrain their endpoints: `query` ends at a `datastore`, `async`
has a `destination` at one or both ends.

The reserved `pattern` value is present in the enum and unused.

### Edge ids

```
<caller>.<callee>.<hash6>
```

The prefix uses node ids verbatim, so it stays readable:
`order.pricing.7f3ac1`.

`hash6` only has to disambiguate edges sharing a caller→callee pair. It is the first 6 lowercase hex of SHA-256 over the six fields that can distinguish them, joined by `U+001F`, nulls as empty strings:

```
caller_endpoint ␟ callee_endpoint ␟ routing_key ␟ headers ␟
selector.expression ␟ role
```


### `async` structural roles

Derived from node kinds, never stored:

| caller.kind → callee.kind | Relation | Fields used |
|---|---|---|
| `service` → `destination` | publish | `routing_key`, `headers` |
| `destination` → `destination` | route | `selector`, `role` |
| `destination` → `service` | deliver | `callee_endpoint` |

`async` edges are meaningful only in composition, a publish edge alone does not imply anything consumes it.

---

## Selectors

On `async` destination→destination edges.

```json
{ "type": "pattern", "syntax": "amqp-topic", "expression": "order.*" }
{ "type": "exact",   "expression": "order.placed" }
{ "type": "all" }
{ "type": "headers", "match": "all", "expression": "event_type=order.placed,region=eu" }
{ "type": "hash",    "expression": "order_id" }
```

```
selector.type    exact · pattern · all · headers · hash
selector.syntax  amqp-topic · mqtt · nats · regex · sql-92 · json-filter
selector.match   all · any                          (headers only)
```

`expression` is always a string. Key-value forms are written as `k=v` pairs sorted by key and joined by `,`, so they stay hashable for edge ids.

This is mostly generalization readiness and primarily internal only, SAR tools are expected to emit only the async-derived edges. This benchmark is using a very small subset of the options above.

---

## Operation naming

Both `caller_endpoint` and `callee_endpoint` use these forms, so an edge's `callee_endpoint` matches the next edge's `caller_endpoint` by string equality. `query` edges are the exception: their `callee_endpoint` is a table or collection name, not an operation.

| Origin | Form |
|---|---|
| HTTP handler | `POST /orders` |
| gRPC handler | `OrderState/Advance` |
| WebSocket handler | `WS /telemetry` |
| Broker consumer | `on:order.placed` |

Path parameters use **named braces** — `GET /orders/{id}`. The name is part of the stored string, and therefore of the edge-id hash, so each endpoint has exactly one spelling: use the callee's own parameter name. Query strings and fragments are excluded — they are not part of endpoint identity. gRPC forms have
no parameters.

Collapsing `{id}` to a placeholder is a matching concern and belongs to the scorer, not to this artifact.

---


## Serialization

- Stable key order, from the schema.
- Every field is present on every node and edge; those that do not apply are
  `null`. Nested objects carry only their applicable keys.
- `nodes` and `edges` both sorted by `id`.
- Fixed two-space indent, trailing newline.

## SDG

The dataset is the source of truth; the SDG is a view over it. To derive one, collapse all edges that share the same `caller` and `callee` into a single edge between those two nodes.
