# PolyEats

A polyglot (Go, Java, Python) microservices benchmark for  software architecture recovery (SAR) tools, built around a food-delivery system. Ground truth ships as an annotated dependency graph: services, datastores and message destinations as nodes, typed endpoint-level edges labelled with the SAR pattern that obscures them and whether each is statically resolvable and/or observed at runtime. See [dataset/dataset-schema.md](dataset/dataset-schema.md). A grader in [grading/](grading/) scores tool output against it.

## Layout

| Path | Contents |
|---|---|
| `services/` | The benchmark's microservices |
| `dataset/` | Published dependency graph + validation report and their schemas |
| `grading/` | Grader and naive baseline |
| `infra/` | Tooling (release stamping, canonicalisation) |
| `proto/` | gRPC definitions |

## Running it

```
docker compose up --build
```

Brings up the entire stack. Jaeger (traces) is available at [http://localhost:16686](http://localhost:16686).

Once everything is healthy, you can run the smoke test against the running stack:

```
python infra/workload/run.py
```

It exercises each service's `/health` and a few real endpoints, and exits non-zero on any unexpected status code.

## Grading

A submission is a JSON file listing the nodes and caller → callee edges your tool recovered:

```json
{
  "nodes": ["address", "geocoding", "db:address"],
  "edges": [
    {"caller": "address", "callee": "geocoding"},
    {"caller": "address", "callee": "db:address"}
  ]
}
```

Services are named after their folder in `services/`, datastores as `db:<name>` named after the service that owns them (`db:geocoding`). Every caller and callee must appear in `nodes`.

```
python grading/grader/grader.py results.json [--dbs]
```

Datastores are ignored unless `--dbs` is passed. The grader prints the number of `correct`, `missing` and `additional` caller → callee pairs. For a reference point, [grading/baselines/baseline.py](grading/baselines/baseline.py) produces a submission with a naive grep: `python grading/baselines/baseline.py services --output results.json`.

## License

Apache-2.0, see [LICENSE](LICENSE).
