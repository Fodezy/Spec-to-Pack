# Spec-to-Pack Studio

Generate high-quality engineering document **packs** from a structured product **spec**. Feed it an Idea + Decisions (or a Source Spec), and it will validate, orchestrate agents, render templates, and emit a consistent artifact set (e.g., PRD, Test Plan, diagrams, roadmaps) along with a machine-readable manifest.

> Status: active development. See the Roadmap section for milestone scope.

---

## Why

Teams waste time rewriting the same docs in different formats. Spec-to-Pack Studio turns a single structured spec into repeatable, validated outputs with:

* **Strong schemas** (JSON Schema 2020-12) for specs and manifests
* **Determinism** (idempotent reruns, golden tests)
* **Clear governance** (template sets with semver, contract checks)
* **Good DX** (helpful CLI, dry-run, audit logs)

---

## What it produces

Two primary “packs” (with more possible later):

* **Balanced Pack v1**
  PRD, Test Plan, lifecycle & sequence diagrams, and a draft roadmap — rendered via agents & templates.

* **Engineering Deep Pack**
  Deep engineering docs, generated JSON/YAML contracts, CI workflow, and a packaged zip with an integrity manifest.

All outputs are tracked in `artifact_index.json` with SHA-256 and template metadata.

---

## CLI at a glance

```bash
# Validate a spec
studiogen validate path/to/source_spec.yaml

# Generate a pack (Balanced by default)
studiogen generate \
  --idea path/to/idea.yaml \
  --decisions path/to/decisions.yaml \
  --out ./out

# Helpful flags (planned/rolling out)
studiogen generate --dry-run           # preview artifacts & diffs
studiogen generate --offline           # no network, enforce guards
studiogen generate --dials path/to/dials.yaml
```

> The CLI name and flags are part of the evolving DX; see milestone notes for WIP.

---

## Project structure (proposed)

```
.
├── cli/                     # CLI entrypoints (studiogen)
├── core/                    # Orchestrator, RunContext, AuditLog
├── schemas/                 # JSON schemas (spec, manifest, contracts)
├── templates/               # Jinja2 templates (template_set semver)
├── agents/                  # Content agents (PRD, diagrams, etc.)
├── contracts/               # Generated schema/contracts for outputs
├── ci/                      # Workflow stubs, CI helpers
├── tests/
│   ├── fixtures/            # Valid/invalid spec samples
│   └── goldens/             # Golden outputs for determinism
└── docs/                    # Docs & troubleshooting
```

Key contracts:

* `schemas/source_spec.schema.json`
* `schemas/artifact_index.schema.json`
* `contracts/*.schema.json` (Deep Pack)

---

## Spec format (sketch)

```yaml
# source_spec.yaml (minimal sketch)
meta:
  name: "Sample Feature"
  version: "0.1.0"
problem:
  statement: "Who/what/why..."
success_metrics:
  - "p95 < 8s end-to-end"
constraints:
  offline_ok: true
decisions:
  # derived or merged from --decisions
  dials:
    research: false
    budget_tokens: 80000
```

---

## Manifest format

`artifact_index.json` (emitted on generate):

```json
{
  "run_id": "2025-01-15T12-01-33Z-8e3a",
  "generated_at": "2025-01-15T12:01:35Z",
  "template_set": "balanced-1.0.0",
  "template_commit": "abc1234",
  "artifacts": [
    {
      "name": "prd.md",
      "purpose": "Product Requirements",
      "pack": "balanced",
      "path": "out/balanced/prd.md",
      "sha256": "…"
    }
  ]
}
```

---

## Determinism & audit

* **Determinism:** reruns with the same inputs should produce byte-identical outputs (except timestamps). We enforce this with golden tests and a CI rerun-diff job.
* **Audit:** JSONL log per run: `{time_iso, level, run_id, stage, event, duration_ms, details}`.

---

## Getting started

### Prereqs

* Python 3.11+ and `pip`/`pipx`
* Make (optional, for developer targets)
* GitHub CLI (`gh`) only if you use the repo bootstrap script

### Install (dev)

```bash
git clone https://github.com/Fodezy/Spec-to-Pack.git
cd Spec-to-Pack
pip install -e .      # or: pipx runpip spec-to-pack install -e .
pre-commit install    # if the repo uses pre-commit hooks
```

### Quick validation

```bash
studiogen validate examples/source_spec.yaml
```

### Generate a pack

```bash
studiogen generate \
  --idea examples/idea.yaml \
  --decisions examples/decisions.yaml \
  --out ./out
```

---

## Template sets & governance

* Templates are grouped into a **template set** with **semver** (e.g., `balanced-1.0.0`).
* Each run embeds `{template_set, template_commit}` into the `artifact_index.json`.
* Breaking template changes require a version bump and a changelog entry.
* A **template harness** renders the smallest valid spec across all templates and fails on missing variables (Jinja2 `StrictUndefined`).

---

## CI & quality gates

* **Schema validation:** source spec, manifest, and contracts validate against their schemas.
* **Linting:** `yamllint`, JSON syntax checks, Mermaid lint for diagrams.
* **Budgets:** step/time budgets enforced by the orchestrator; regressions blocked by CI.
* **Performance:** p95 gates + regression thresholds (e.g., >20% fail).

---

## Optional: Librarian & RAG (M4)

When `--research` is enabled (opt-in), the Librarian can fetch, clean, and embed content with provenance (e.g., LanceDB/Qdrant). Guards ensure offline mode blocks all network access and respects `robots.txt` when online.

---

## Repo automation (Issues/Epics/Milestones)

Use the bootstrap script to scaffold labels, milestones, epics, and child tasks in GitHub.

```bash
# Preview (no changes; gh auth not required)
./bootstrap_issues.sh Fodezy/Spec-to-Pack --dry-run

# Real run (requires gh auth)
gh auth login
./bootstrap_issues.sh Fodezy/Spec-to-Pack
```

The script is idempotent and appends checklists of child issues to their epics.

---

## Roadmap (milestones)

| Milestone                            | Theme                    | Highlights                                                         |
| ------------------------------------ | ------------------------ | ------------------------------------------------------------------ |
| **M0 — Foundations & Schemas**       | Scaffolding & validation | Repo layout, CI matrix, schemas, validator, fixtures               |
| **M1 — Spec Builder & Orchestrator** | Merge/Frame + runtime    | SpecBuilder, Framer-lite, budgets/timeouts, audit                  |
| **M2 — Balanced Pack v1**            | Agents + templates       | PRD/Test Plan/Diagrams/Roadmap, template harness, E2E & perf gates |
| **M3 — Engineering Deep Pack**       | Deep docs & contracts    | Generated contracts, CI workflow, packager + manifest integrity    |
| **M4 — Librarian & RAG (optional)**  | Research w/ provenance   | Librarian, vector store, offline/robots guards                     |
| **M5 — Hardening & DX**              | Quality & usability      | Mutation/property/golden tests, CLI UX, troubleshooting docs       |

---

## Contributing

1. **Fork & branch**: `feat/*`, `fix/*`.
2. **Run checks**: `make test` (or `pytest`), `pre-commit run -a`.
3. **Add tests** for new behavior (schema, golden, E2E as appropriate).
4. **Open a PR** with a clear description and link to the tracked issue/epic.

Labels you’ll see: `type: epic`, `type: task`, `area:*`, and `milestone:*`.

---

## Troubleshooting

* **Validation fails:** run `studiogen validate <spec>` and fix the JSON-pointer errors.
* **Missing template variables:** harness or generation will fail fast; check template and spec.
* **Non-deterministic outputs:** ensure timestamps/random seeds are normalized; compare with goldens.
* **Offline runs still fetch:** confirm `--offline` is set; tests should monkey-patch sockets and fail on any HTTP calls.
* **Bootstrap script errors:** ensure `gh auth status` is OK; the script uses REST via `gh api`.

---

## License

See `LICENSE` in this repository.

---

## Acknowledgments

Built with a bias toward **clarity, contracts, and repeatability** so docs stay trustworthy — and engineers stay sane.
