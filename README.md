# PolyEats

A polyglot microservices benchmark for service architecture recovery (SAR) tools, built around a food-delivery system. Ground truth ships as a Service Dependency Graph (SDG) — see [dataset/dataset-schema.md](dataset/dataset-schema.md).

## Layout

| Path | Contents |
|---|---|
| `services/` | The benchmark's microservices |
| `dataset/` | Published SDG + validation report and their schemas |
| `infra/` | Tooling (release stamping, canonicalisation) |
| `proto/` | gRPC definitions |

## License

Apache-2.0, see [LICENSE](LICENSE).
