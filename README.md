# PolyEats

A polyglot microservices benchmark for service architecture recovery (SAR) tools, built around a food-delivery system. Ground truth ships as a Service Dependency Graph (SDG) — see [dataset/dataset-schema.md](dataset/dataset-schema.md).

## Layout

| Path | Contents |
|---|---|
| `services/` | The benchmark's microservices |
| `dataset/` | Published SDG + validation report and their schemas |
| `infra/` | Tooling (release stamping, canonicalisation) |
| `proto/` | gRPC definitions |

## Running it

```
docker compose up --build
```

Brings up all services plus Jaeger. Traces: [http://localhost:16686](http://localhost:16686). REST ports: geocoding `8000`, order-tracking `8001`, address `8002`.

Once everything is healthy, run the smoke test against the running stack:

```
python infra/workload/run.py
```

It exercises each service's `/health` and a few real endpoints, and exits non-zero on any unexpected status code.

## Regenerating protos

```
./proto/build.sh
```

Regenerates the Go and Python gRPC stubs from [proto/geocoding.proto](proto/geocoding.proto) and copies the `.proto` file into the address service (Java compiles it at build time).

## License

Apache-2.0, see [LICENSE](LICENSE).
