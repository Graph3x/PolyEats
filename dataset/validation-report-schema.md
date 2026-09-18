# PolyEats - validation report schema version 1.1.1

Specification for `validation-report.json`: the rater-agreement evidence
behind a `connections.json` release.

---

## `validation-report.json` - top level

| Field | Type | Required | Notes |
|---|---|---|---|
| `schema_version` | string | yes | semver of this schema |
| `dataset_version` | string | yes (on release) | semver of the `connections.json` release this report validates |
| `timestamp` | iso timestamp (utc) | yes (on release) | |
| `raters` | array | yes (on release) | one entry per rater who independently compared against the published `connections.json` |
| `notes` | string | no | e.g. why `raters` is empty, adjudication summary |

### `raters[]`

| Field | Type | Notes |
|---|---|---|
| `role` | enum | `maintainer` \| `external` — no names or other PID |
| `kappa` | object | Cohen's κ against the published `connections.json`, per facet |

```
kappa.callee     agreement on callee identity        (number)
kappa.pattern    agreement on pattern classification  (number)
```

Reported **pre-adjudication** — that is the honest reproducibility number.
Final edge labels in `connections.json` are the post-adjudication
consensus; this report does not restate them.

An empty `raters` array means no independent rater has compared yet — expected until the full release.

---

## Serialization

- Stable key order, from the schema.
- Fixed two-space indent, trailing newline.
