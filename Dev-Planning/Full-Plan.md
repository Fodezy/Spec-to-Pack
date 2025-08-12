Got it—here’s the same plan, **restructured by Milestone → Epic → Issues/Tasks**, with acceptance criteria sitting right under the piece they belong to. This should drop cleanly into a tracker.

# Spec-to-Pack Studio — Deep Engineering Plan (v2.1)

## Global definitions & policies (apply to all milestones)

* **DoR:** clear title, unambiguous story & AC, inputs available/validated, deps identified.
* **DoD:** AC met, PR reviewed/merged to `main`, **diff coverage ≥85%** for changed code, **mutation ≥70%** on targeted modules, docs updated, CI green on **Linux/macOS/Windows**.
* **Determinism:** byte-stable outputs; JSON sorted keys, LF newlines, UTC; timestamps only in `artifact_index.generated_at`; CI rerun-diff job.
* **Template governance:** Jinja2 **StrictUndefined**; versioned **template\_set** (semver) with commit hash embedded in manifest; template harness renders every template with smallest valid spec; goldens for 3–5 core templates.
* **Schema governance:** `meta.spec_version` (semver); refuse render if `spec_version > engine_supported` (unless `--force`); `spec_migrations/` + `studiogen migrate`.
* **Security/Privacy:** Offline mode blocks sockets in tests; SBOM + Dependabot + CodeQL; logs scrub PII/abs paths.
* **Cross-platform:** path/Unicode normalization; Windows reserved names & path length tests; CI matrix must produce identical artifact hashes across OSes.
* **Perf gate:** fixed fixtures, warmed cache; Balanced pack p95 ≤ **8s**; fail on > **20%** regression.

---

# Milestone M0 — Foundations & Schemas (1 week)

**Goal:** Stable repo, core contracts, validation CLI, determinism & CI matrix.

## Epic M0.E1 — Project Scaffold & CI

**Issues/Tasks**

* **CORE-1:** Create repo per R4 structure.
* **CORE-2:** Add CI workflow (lint + unit) with **Linux/macOS/Windows** matrix.
* **CORE-3:** Pre-commit hooks (ruff, black, isort, yamllint).
* **CORE-4:** Add determinism layer + CI **rerun-diff** job.

**Acceptance**

* Repo matches R4 layout; hooks run on commit.
* CI triggers on PR; lint/test jobs pass on all OSes.
* Two successive runs produce identical bytes (only `generated_at` differs).

## Epic M0.E2 — Core Schemas & Validator

**Issues/Tasks**

* **SPEC-1:** Draft `source_spec.schema.json` (Draft 2020-12).
* **SPEC-2:** Draft `artifact_index.schema.json` + examples.
* **SPEC-3:** Implement `SchemaValidator.validate(data, schema) -> ValidationResult`.
* **SPEC-4:** Fixtures for valid/invalid specs; self-validation of schemas.

**Acceptance**

* Schemas validate with meta-schema; invalid fixture emits JSON-pointer errors.
* Validator returns `{ok, errors[]}` with pointers & messages.

## Epic M0.E3 — Validation CLI & Audit Stubs

**Issues/Tasks**

* **CLI-1:** `studiogen validate --spec path.json` (file-not-found handled).
* **CORE-5:** Stubs: `RunContext`, `AuditLog` (JSONL format defined).

**Acceptance**

* Valid spec → exit 0; invalid spec → exit 2 + structured errors.
* Audit JSONL written with `{time_iso, level, run_id, stage, event}`.

**M0 Deliverable:** Dev can clone, install, and run `studiogen validate` successfully.

---

# Milestone M1 — Spec Builder & Orchestrator (1–2 weeks)

**Goal:** Turn Idea + Decisions into a valid Spec; orchestrate a stub pipeline end-to-end.

## Epic M1.E1 — Spec Builder & Framer-lite

**Issues/Tasks**

* **SPEC-5:** `SpecBuilder` merges Idea Card + Decision Sheet → `SourceSpec`.
* **SPEC-6:** **FramerAgent-lite** fills required empty fields with placeholders; logs overrides.

**Acceptance**

* Output spec passes schema validation.
* Dials from Decision Sheet reflected in spec; overrides logged.

## Epic M1.E2 — Orchestrator & Runtime

**Issues/Tasks**

* **ORCH-1:** Orchestrator state machine per R1 (guards/budgets/timeouts).
* **ORCH-2:** Implement **BudgetExceeded** / **StepTimeout** errors.
* **CORE-6:** `RunContext` finalized (offline flag), `AuditLog` durations added.

**Acceptance**

* Orchestrator runs stub agents within step/time budgets.
* Audit JSONL shows: CollectInputs → ValidateSpec → RenderPacks events.

## Epic M1.E3 — Generate Command & TemplateRenderer (stub)

**Issues/Tasks**

* **CLI-2:** `studiogen generate --idea --decisions --pack balanced -o out/`.
* **TMPL-1:** Minimal `TemplateRenderer` (Jinja2 **StrictUndefined**).
* **TMPL-2:** Render **stub** `brief.md` + empty `artifact_index.json`.

**Acceptance**

* Command produces `brief.md` and `artifact_index.json` in `out/`.
* Idempotent rerun → zero diffs (except `generated_at`).

**M1 Deliverable:** Minimal **Balanced** pack skeleton generated in CI.

---

# Milestone M2 — Balanced Pack v1 (1–2 weeks)

**Goal:** Produce full Balanced pack via content agents & templates.

## Epic M2.E1 — Content Agents (Balanced)

**Issues/Tasks**

* **AGENT-1:** `PRDWriterAgent` → `prd.md`, `test_plan.md`.
* **AGENT-2:** `DiagrammerAgent` → `lifecycle.mmd`, `sequence_*.mmd`.
* **AGENT-3:** `RoadmapperAgent` → `roadmap.md`.
* **AGENT-4:** `QAArchitectAgent` injects AC & matrix into test plan.

**Acceptance**

* Docs populated per R2 field mapping; no missing vars (StrictUndefined).
* Mermaid passes lint.

## Epic M2.E2 — Template Set & Governance

**Issues/Tasks**

* **TPL-1:** Establish `template_set` semver; embed `{template_set, template_commit}` into manifest.
* **TPL-2:** Template harness test renders **all** templates with smallest valid spec.
* **TPL-3:** Golden tests for 3–5 core templates (brief/prd/roadmap/test\_plan).

**Acceptance**

* Harness & goldens pass in CI; any missing var fails fast.

## Epic M2.E3 — E2E, Contracts & Performance

**Issues/Tasks**

* **TEST-1:** Implement BDD from R3 (Idea→Balanced Pack).
* **CNTR-1:** Contract test Orchestrator ↔ TemplateRenderer (data shape).
* **PERF-1:** Perf capture; Balanced p95 baseline; regression budget in CI.

**Acceptance**

* E2E BDD passes; p95 ≤ 8s (warm); failure if >20% regression vs baseline.
* Artifact index complete & correct for Balanced pack.

**M2 Deliverable:** Complete Balanced pack generated deterministically under CI.

---

# Milestone M3 — Engineering Deep Pack (1–2 weeks)

**Goal:** Generate deep pack docs, contracts, CI workflow; add packager & validation.

## Epic M3.E1 — Deep Docs & Contracts

**Issues/Tasks**

* **AGENT-5:** Deep docs: `prd_engineering_deep.md`, `threat_model.md`, `accessibility.md`, `observability.md`, `runbooks.md`, `slos.md`, `adr_index.md`, `ADR-0001.md`.
* **AGENT-6:** Generate `ci/workflow.yml` from spec ops; generate `contracts/*.schema.json`.

**Acceptance**

* All deep docs render with StrictUndefined; YAML/JSON syntactically valid.
* JSON Schemas validate against meta-schema; YAML passes yamllint.

## Epic M3.E2 — Packager & Manifest Integrity

**Issues/Tasks**

* **PKG-1:** `PackagerAgent` produces zips; compute **SHA-256** per artifact.
* **PKG-2:** `artifact_index.json` lists `{purpose, pack, sha256, template_set, template_commit}` for all files.

**Acceptance**

* Zips contain all artifacts; manifest hashes match file content.

## Epic M3.E3 — Output Validation in CI

**Issues/Tasks**

* **VALID-1:** CI step validates all rendered JSON/YAML contracts & workflow.
* **TEST-2:** E2E “Deep Pack” from R3; add contract tests for generated schemas.

**Acceptance**

* Deep E2E passes; schema & workflow validation succeed on all OSes.

**M3 Deliverable:** Balanced **and** Deep packs generate & validate end-to-end.

---

# Milestone M4 — Librarian & Optional RAG (1–2 weeks, optional)

**Goal:** Opt-in research with provenance; enrich PRD with “Evidence.”

## Epic M4.E1 — Librarian & Stores

**Issues/Tasks**

* **LIB-1:** `LibrarianAgent` + `BrowserAdapter` (Playwright).
* **LIB-2:** `VectorStoreAdapter` (LanceDB/Qdrant) + **bge-small** embeddings.
* **LIB-3:** Provenance model `{source_url, retrieved_at, chunk_id}`.

**Acceptance**

* Can fetch, clean, embed; embeddings stored locally with provenance.

## Epic M4.E2 — RAG Integration & Guards

**Issues/Tasks**

* **RAG-1:** PRD “Evidence” section with citations.
* **GUARD-1:** Offline mode blocks network (socket monkeypatch in tests).
* **GUARD-2:** Max tokens per doc; respect robots.txt (if web enabled).

**Acceptance**

* `--research` populates Evidence; default offline mode performs zero network calls.

**M4 Deliverable:** Evidence-enriched packs when explicitly enabled.

---

# Milestone M5 — Hardening & DX Polish (1 week)

**Goal:** Resilience, usability, and developer experience.

## Epic M5.E1 — CLI UX & Dry-Run

**Issues/Tasks**

* **DX-1:** Flags `--dials audience=Balanced,flow=Dual-Track,test=Pyramid`, `--offline`, `--dry-run`.
* **DX-2:** Helpful error messages with JSON pointers & hints.
* **DX-3:** **Dry-run preview** lists artifacts to be generated & diffs vs prior run.

**Acceptance**

* CLI help is clear; dry-run output actionable & readable.

## Epic M5.E2 — Advanced Quality Checks

**Issues/Tasks**

* **MUT-1:** Mutation tests (mutmut) on rename/tag/link selection & SpecBuilder mapping.
* **PROP-1:** Property tests (hypothesis) for idempotency & determinism.
* **GOLD-1:** Golden tests stabilize; `make goldens-regen` workflow.

**Acceptance**

* Mutation ≥ 70% on targeted modules; property tests pass; golden updates explicit.

## Epic M5.E3 — Docs & Troubleshooting

**Issues/Tasks**

* **DOC-1:** Troubleshooting guide (schema failures, Mermaid, path issues).
* **DOC-2:** Template changelog policy & versioning doc.
* **DOC-3:** Spec migration policy & `migrate` usage.

**Acceptance**

* Docs published; dev can resolve common failures in <10 minutes.

**M5 Deliverable:** Robust, deterministic v1.0 with strong DX.

---

# Cross-cutting optional epics (run in parallel where useful)

## X1 — Localization (LOC-I18N)

* Localized template bundles; `meta.locale`; date/number formatting.
* AC: `--locale fr-CA` renders French headings; English fallback safe.

## X2 — Plugin/Registry (PLUGIN-REG)

* Discover agents/templates via entry points; `studiogen init --use vendor/mypack`.
* AC: third-party pack renders via same pipeline & validation gates.

## X3 — Release & Distribution (REL-DIST)

* Package to PyPI; optional PyInstaller single binary; Homebrew tap.
* AC: `pipx install studiogen` → `studiogen init` and `generate` work on fresh machine.

## X4 — Observability Report (OBS-REP)

* Local HTML run report (counts, timings, pass/fail, links).
* AC: `out/run_report.html` emitted with each run; weekly rollup optional.

---

# Quality gates (per milestone)

* **Always:** schema validation ✓, unit ✓, lint/format ✓, determinism ✓, CI matrix ✓.
* **M2+:** BDD e2e ✓, Mermaid lint ✓, perf p95 & regression ✓.
* **M3+:** JSON/YAML contract validation ✓, manifest completeness (sha256 + template metadata) ✓.
* **M5:** mutation ≥ 70% on targeted modules; property tests for idempotency ✓.

---

# Risks & mitigations (unchanged but grouped)

* **Template drift / omissions** → StrictUndefined + harness + goldens.
* **Spec evolution breaks users** → spec\_version gating + migration CLI/tests.
* **Cross-platform anomalies** → matrix + path/encoding normalization + reserved name checks.
* **Perf flakiness** → fixed fixtures, warmed cache, regression threshold.
* **Security regression** → CodeQL + SBOM + offline tests + scrubbed logs.

---

# Immediate next steps (48h)

1. Implement determinism utilities + CI **rerun-diff** job.
2. Switch to Jinja2 **StrictUndefined**; add template harness test.
3. Add `template_set` metadata + changelog skeleton; embed commit hash in manifest.
4. Pin Mermaid CLI & lint; extend CI to **Windows/macOS**.
5. Add `meta.spec_version`; stub `studiogen migrate` with a failing test (red → green).


