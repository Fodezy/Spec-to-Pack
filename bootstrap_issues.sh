#!/usr/bin/env bash
set -euo pipefail

# Bootstrap GitHub milestones, epics, and issues for Spec-to-Pack Studio (v2.1)
# Requires: GitHub CLI (gh) authenticated with repo write access.
# Usage: ./bootstrap_issues.sh owner/repo [--dry-run]

REPO="${1:-}"
DRY_RUN="${2:-}"

if [[ -z "${REPO}" ]]; then
  echo "Usage: $0 owner/repo [--dry-run]" >&2
  exit 1
fi

if ! command -v gh >/dev/null 2>&1; then
  echo "Error: gh CLI not found. Install https://cli.github.com/ and run 'gh auth login'." >&2
  exit 1
fi

purple() { printf "\033[35m%s\033[0m\n" "$*"; }
green()  { printf "\033[32m%s\033[0m\n" "$*"; }
yellow() { printf "\033[33m%s\033[0m\n" "$*"; }

# Run a command or just print it in dry-run mode
run() {
  if [[ "${DRY_RUN}" == "--dry-run" ]]; then
    yellow "[dry-run] $*"
  else
    "$@"
  fi
}

# Create label if missing (idempotent)
ensure_label() {
  local name="$1" color="$2" desc="$3"
  if gh label list -R "$REPO" --limit 200 --json name --jq '.[].name' | grep -Fxq "$name"; then
    yellow "Label exists: $name"
  else
    run gh label create -R "$REPO" "$name" --color "$color" --description "$desc"
  fi
}

# Create milestone if missing (idempotent). Echoes the title.
ensure_milestone() {
  local title="$1" desc="$2"
  if gh api "repos/${REPO}/milestones?state=all" --jq '.[].title' | grep -Fxq "$title"; then
    yellow "Milestone exists: $title" >&2
  else
    # Use -f "key=value" to avoid quoting issues; description may contain newlines.
    if [[ "${DRY_RUN}" == "--dry-run" ]]; then
      yellow "[dry-run] gh api -X POST repos/${REPO}/milestones -f title=\"$title\" -f description=\"(omitted)\"" >&2
    else
      gh api -X POST "repos/${REPO}/milestones" \
        -f "title=${title}" \
        -f "description=${desc}" >/dev/null
      green "Created milestone: $title" >&2
    fi
  fi
  echo "$title"
}

# Create issue if missing by exact title. Echoes issue number (or 0 in dry-run).
ensure_issue() {
  local title="$1" body="$2" labels_csv="$3" milestone_title="$4"

  local existing
  existing="$(gh issue list -R "$REPO" --search "$title in:title" --limit 200 --json number,title \
             --jq ".[] | select(.title==\"$title\") | .number" || true)"
  if [[ -n "${existing}" ]]; then
    yellow "Issue exists: #${existing}  $title"
    echo "$existing"
    return
  fi

  # Write body to a temp file to avoid quoting issues
  local bodyfile
  bodyfile="$(mktemp --tmpdir gh_issue_body.XXXXXX)"
  printf "%s" "$body" >"$bodyfile"

  # Build args array
  local args=(issue create -R "$REPO" --title "$title" --body-file "$bodyfile" --milestone "$milestone_title")

  # Labels
  IFS=',' read -r -a LBL <<< "$labels_csv"
  for l in "${LBL[@]}"; do
    [[ -n "$l" ]] && args+=( --label "$l" )
  done

  local num="0"
  if [[ "${DRY_RUN}" == "--dry-run" ]]; then
    yellow "[dry-run] gh ${args[*]}"
  else
    local output
    output="$(gh "${args[@]}" 2>&1)"
    # Extract issue number from URL output like "https://github.com/owner/repo/issues/42"
    num="$(echo "$output" | grep -oE 'https://github.com/[^/]+/[^/]+/issues/[0-9]+' | grep -oE '[0-9]+$' | head -1 || echo "0")"
    green "Created issue #$num  $title"
  fi

  rm -f "$bodyfile"
  echo "$num"
}

# Append checklist items to an epic body
append_checklist_to_epic() {
  local epic_num="$1"; shift
  local checklist=""
  for child in "$@"; do
    [[ -n "$child" && "$child" != "0" ]] && checklist+="- [ ] #$child"$'\n'
  done
  [[ -z "$checklist" ]] && return 0

  if [[ "${DRY_RUN}" == "--dry-run" ]]; then
    yellow "[dry-run] append checklist to epic #$epic_num:"
    printf "%s" "$checklist"
    return 0
  fi

  # For now, skip updating epic bodies due to CLI compatibility issues
  # The issues are created with proper labels and milestones for tracking
  yellow "Skipping epic checklist update for #$epic_num (CLI compatibility)"
}

###############################################################################
# 1) Labels
###############################################################################
purple "==> Ensuring labels"
ensure_label "type: epic"        "5319e7" "High-level epic"
ensure_label "type: task"        "1f883d" "Implementation task"
ensure_label "area: core"        "0e8a16" "Core scaffolding & orchestrator"
ensure_label "area: schema"      "c2e0c6" "Schemas & validation"
ensure_label "area: cli"         "fbca04" "CLI & DX"
ensure_label "area: agents"      "0052cc" "Content agents"
ensure_label "area: templates"   "5319e7" "Template set & governance"
ensure_label "area: ci"          "f66a0a" "CI/CD & workflows"
ensure_label "area: perf"        "e99695" "Performance"
ensure_label "area: security"    "b60205" "Security/Privacy"
ensure_label "area: docs"        "0366d6" "Documentation"
ensure_label "milestone: M0"     "ededed" "Foundations & Schemas"
ensure_label "milestone: M1"     "ededed" "Spec Builder & Orchestrator"
ensure_label "milestone: M2"     "ededed" "Balanced Pack v1"
ensure_label "milestone: M3"     "ededed" "Engineering Deep Pack"
ensure_label "milestone: M4"     "ededed" "Librarian & RAG"
ensure_label "milestone: M5"     "ededed" "Hardening & DX"

###############################################################################
# 2) Milestones → Epics → Issues
###############################################################################
ml_body() { cat; }  # helper to make heredocs less noisy

########################################
# M0 — Foundations & Schemas
########################################
M0_TITLE="$(ensure_milestone "M0 — Foundations & Schemas" "$(ml_body <<'TXT'
Stable repo, core contracts, validation CLI, determinism & CI matrix.
TXT
)")"

E_M0_E1=$(ensure_issue "M0.E1 — Project Scaffold & CI" "$(ml_body <<'TXT'
**Goal:** Repo scaffolding, CI matrix, determinism job.

**Acceptance**
- Repo matches R4 layout; hooks run on commit.
- CI matrix green (Linux/macOS/Windows).
- Rerun-diff job: two successive runs identical (except generated_at).
TXT
)" "milestone: M0,area: core,type: epic" "$M0_TITLE")

I_CORE1=$(ensure_issue "CORE-1: Create repo per R4 structure" "$(ml_body <<'TXT'
**AC**
- Directory layout matches R4 scaffold.
- README + pyproject.toml stubbed.
TXT
)" "milestone: M0,area: core,type: task" "$M0_TITLE")
I_CORE2=$(ensure_issue "CORE-2: Add CI workflow (lint+unit) with OS matrix" "$(ml_body <<'TXT'
**AC**
- GitHub Actions runs on Linux, macOS, Windows.
- Lint & unit stages pass on PR.
TXT
)" "milestone: M0,area: ci,type: task" "$M0_TITLE")
I_CORE3=$(ensure_issue "CORE-3: Pre-commit hooks (ruff/black/isort/yamllint)" "$(ml_body <<'TXT'
**AC**
- Hooks installed via pre-commit.
- Running 'git commit' triggers checks.
TXT
)" "milestone: M0,area: core,type: task" "$M0_TITLE")
I_CORE4=$(ensure_issue "CORE-4: Determinism utilities + rerun-diff CI job" "$(ml_body <<'TXT'
**AC**
- JSON sort keys, LF newlines, UTC timestamps.
- CI job compares two runs; no diffs except generated_at.
TXT
)" "milestone: M0,area: perf,type: task" "$M0_TITLE")
append_checklist_to_epic "$E_M0_E1" "$I_CORE1" "$I_CORE2" "$I_CORE3" "$I_CORE4"

E_M0_E2=$(ensure_issue "M0.E2 — Core Schemas & Validator" "$(ml_body <<'TXT'
**Goal:** Draft JSON Schemas & validator.

**Acceptance**
- Schemas validate against Draft 2020-12 meta-schema.
- Validator returns {ok, errors[pointer,message]}.
TXT
)" "milestone: M0,area: schema,type: epic" "$M0_TITLE")
I_SPEC1=$(ensure_issue "SPEC-1: Draft source_spec.schema.json" "$(ml_body <<'TXT'
**AC**
- Covers meta/problem/constraints/success_metrics/etc.
- Example spec validates.
TXT
)" "milestone: M0,area: schema,type: task" "$M0_TITLE")
I_SPEC2=$(ensure_issue "SPEC-2: Draft artifact_index.schema.json + examples" "$(ml_body <<'TXT'
**AC**
- Manifest includes {run_id, generated_at, artifacts[name,purpose,pack,path]}.
TXT
)" "milestone: M0,area: schema,type: task" "$M0_TITLE")
I_SPEC3=$(ensure_issue "SPEC-3: Implement SchemaValidator (ValidationResult)" "$(ml_body <<'TXT'
**AC**
- validate(data,schema)->{ok,errors[]} with JSON pointers.
TXT
)" "milestone: M0,area: schema,type: task" "$M0_TITLE")
I_SPEC4=$(ensure_issue "SPEC-4: Fixtures for valid/invalid specs & self-validation" "$(ml_body <<'TXT'
**AC**
- CI job validates fixtures; invalid prints pointers.
TXT
)" "milestone: M0,area: schema,type: task" "$M0_TITLE")
append_checklist_to_epic "$E_M0_E2" "$I_SPEC1" "$I_SPEC2" "$I_SPEC3" "$I_SPEC4"

E_M0_E3=$(ensure_issue "M0.E3 — Validation CLI & Audit stubs" "$(ml_body <<'TXT'
**Goal:** Validation CLI + audit JSONL format.

**Acceptance**
- validate exits 0/2 on valid/invalid.
- Audit JSONL has {time_iso, level, run_id, stage, event}.
TXT
)" "milestone: M0,area: cli,type: epic" "$M0_TITLE")
I_CLI1=$(ensure_issue "CLI-1: 'studiogen validate' command" "$(ml_body <<'TXT'
**AC**
- Handles file-not-found gracefully.
- Prints structured errors.
TXT
)" "milestone: M0,area: cli,type: task" "$M0_TITLE")
I_CORE5=$(ensure_issue "CORE-5: RunContext & AuditLog (JSONL) stubs" "$(ml_body <<'TXT'
**AC**
- Types defined; written to disk on validate.
TXT
)" "milestone: M0,area: core,type: task" "$M0_TITLE")
append_checklist_to_epic "$E_M0_E3" "$I_CLI1" "$I_CORE5"

########################################
# M1 — Spec Builder & Orchestrator
########################################
M1_TITLE="$(ensure_milestone "M1 — Spec Builder & Orchestrator" "Idea+Decisions → Spec; orchestrate stub pipeline.")"

E_M1_E1=$(ensure_issue "M1.E1 — Spec Builder & Framer-lite" "$(ml_body <<'TXT'
**Goal:** Merge Idea+Decisions; fill required gaps.

**Acceptance**
- Output spec validates.
- Dials from Decision Sheet reflected; overrides logged.
TXT
)" "milestone: M1,area: core,type: epic" "$M1_TITLE")
I_SPEC5=$(ensure_issue "SPEC-5: SpecBuilder merges Idea+Decision → SourceSpec" "$(ml_body <<'TXT'
**AC**
- Dials applied; constraints merged.
TXT
)" "milestone: M1,area: schema,type: task" "$M1_TITLE")
I_SPEC6=$(ensure_issue "SPEC-6: FramerAgent-lite fills required fields" "$(ml_body <<'TXT'
**AC**
- Placeholder text added for missing mandatory fields; override log written.
TXT
)" "milestone: M1,area: agents,type: task" "$M1_TITLE")
append_checklist_to_epic "$E_M1_E1" "$I_SPEC5" "$I_SPEC6"

E_M1_E2=$(ensure_issue "M1.E2 — Orchestrator & Runtime" "$(ml_body <<'TXT'
**Goal:** State machine with budgets/timeouts; rich audit.

**Acceptance**
- Runs within step/time budgets; errors BudgetExceeded/StepTimeout raised.
- Audit includes durations.
TXT
)" "milestone: M1,area: core,type: epic" "$M1_TITLE")
I_ORCH1=$(ensure_issue "ORCH-1: Implement state machine (R1)" "$(ml_body <<'TXT'
**AC**
- Guards for offline/research; retries/backoff as spec'd.
TXT
)" "milestone: M1,area: core,type: task" "$M1_TITLE")
I_ORCH2=$(ensure_issue "ORCH-2: Enforce step budgets & timeouts" "$(ml_body <<'TXT'
**AC**
- Configurable; unit tests for budget/timeout.
TXT
)" "milestone: M1,area: perf,type: task" "$M1_TITLE")
I_CORE6=$(ensure_issue "CORE-6: Finalize RunContext & enrich AuditLog" "$(ml_body <<'TXT'
**AC**
- Fields: time_iso, level, run_id, stage, event, duration_ms, details.
TXT
)" "milestone: M1,area: core,type: task" "$M1_TITLE")
append_checklist_to_epic "$E_M1_E2" "$I_ORCH1" "$I_ORCH2" "$I_CORE6"

E_M1_E3=$(ensure_issue "M1.E3 — Generate command & TemplateRenderer (stub)" "$(ml_body <<'TXT'
**Goal:** Minimal generate flow renders stub brief & manifest.

**Acceptance**
- brief.md + artifact_index.json emitted; idempotent rerun.
TXT
)" "milestone: M1,area: cli,type: epic" "$M1_TITLE")
I_CLI2=$(ensure_issue "CLI-2: 'studiogen generate' (balanced, out dir)" "$(ml_body <<'TXT'
**AC**
- Accepts idea & decisions; writes to out/.
TXT
)" "milestone: M1,area: cli,type: task" "$M1_TITLE")
I_TMPL1=$(ensure_issue "TMPL-1: TemplateRenderer (Jinja2 StrictUndefined)" "$(ml_body <<'TXT'
**AC**
- Renders with smallest valid spec; fails fast on missing vars.
TXT
)" "milestone: M1,area: templates,type: task" "$M1_TITLE")
I_TMPL2=$(ensure_issue "TMPL-2: Emit stub brief.md + artifact_index.json" "$(ml_body <<'TXT'
**AC**
- Manifest validates against schema.
TXT
)" "milestone: M1,area: templates,type: task" "$M1_TITLE")
append_checklist_to_epic "$E_M1_E3" "$I_CLI2" "$I_TMPL1" "$I_TMPL2"

########################################
# M2 — Balanced Pack v1
########################################
M2_TITLE="$(ensure_milestone "M2 — Balanced Pack v1" "Full Balanced pack via agents & templates; governance & perf baseline.")"

E_M2_E1=$(ensure_issue "M2.E1 — Content Agents (Balanced)" "$(ml_body <<'TXT'
**Goal:** PRD/TestPlan/Diagrams/Roadmap via agents.

**Acceptance**
- Docs follow R2 mappings; Mermaid lints.
TXT
)" "milestone: M2,area: agents,type: epic" "$M2_TITLE")
I_AGENT1=$(ensure_issue "AGENT-1: PRDWriterAgent → prd.md & test_plan.md" "$(ml_body <<'TXT'
**AC**
- Sections populated; no missing vars.
TXT
)" "milestone: M2,area: agents,type: task" "$M2_TITLE")
I_AGENT2=$(ensure_issue "AGENT-2: DiagrammerAgent → lifecycle/sequence" "$(ml_body <<'TXT'
**AC**
- Mermaid syntax valid; lint passes.
TXT
)" "milestone: M2,area: agents,type: task" "$M2_TITLE")
I_AGENT3=$(ensure_issue "AGENT-3: RoadmapperAgent → roadmap.md" "$(ml_body <<'TXT'
**AC**
- Milestones include exit criteria referencing AC/NFR IDs.
TXT
)" "milestone: M2,area: agents,type: task" "$M2_TITLE")
I_AGENT4=$(ensure_issue "AGENT-4: QAArchitectAgent integrates AC/matrix" "$(ml_body <<'TXT'
**AC**
- Test Plan includes BDD/contract/property/perf targets.
TXT
)" "milestone: M2,area: agents,type: task" "$M2_TITLE")
append_checklist_to_epic "$E_M2_E1" "$I_AGENT1" "$I_AGENT2" "$I_AGENT3" "$I_AGENT4"

E_M2_E2=$(ensure_issue "M2.E2 — Template Set & Governance" "$(ml_body <<'TXT'
**Goal:** Versioned template_set + harness + goldens.

**Acceptance**
- template_set + commit embedded; harness & golden tests pass.
TXT
)" "milestone: M2,area: templates,type: epic" "$M2_TITLE")
I_TPL1=$(ensure_issue "TPL-1: Establish template_set semver + embed metadata" "$(ml_body <<'TXT'
**AC**
- Manifest includes template_set & template_commit.
TXT
)" "milestone: M2,area: templates,type: task" "$M2_TITLE")
I_TPL2=$(ensure_issue "TPL-2: Template harness (smallest valid spec)" "$(ml_body <<'TXT'
**AC**
- Renders every template; fails on missing vars.
TXT
)" "milestone: M2,area: templates,type: task" "$M2_TITLE")
I_TPL3=$(ensure_issue "TPL-3: Golden tests for core templates" "$(ml_body <<'TXT'
**AC**
- Goldens under tests/goldens; regen via make target.
TXT
)" "milestone: M2,area: templates,type: task" "$M2_TITLE")
append_checklist_to_epic "$E_M2_E2" "$I_TPL1" "$I_TPL2" "$I_TPL3"

E_M2_E3=$(ensure_issue "M2.E3 — E2E, Contracts & Performance" "$(ml_body <<'TXT'
**Goal:** E2E BDD; contract tests; p95 baseline & regression gate.

**Acceptance**
- Balanced E2E passes; p95 ≤ 8s; regression >20% fails.
TXT
)" "milestone: M2,area: ci,type: epic" "$M2_TITLE")
I_TEST1=$(ensure_issue "TEST-1: BDD Idea→Balanced Pack" "$(ml_body <<'TXT'
**AC**
- Uses fixtures; Mermaid lint step.
TXT
)" "milestone: M2,area: ci,type: task" "$M2_TITLE")
I_CNTR1=$(ensure_issue "CNTR-1: Contract test Orchestrator↔Renderer" "$(ml_body <<'TXT'
**AC**
- Data shape validated; failures descriptive.
TXT
)" "milestone: M2,area: ci,type: task" "$M2_TITLE")
I_PERF1=$(ensure_issue "PERF-1: Perf capture & regression budget" "$(ml_body <<'TXT'
**AC**
- Warmed cache; CPU/mem logged; regression gate active.
TXT
)" "milestone: M2,area: perf,type: task" "$M2_TITLE")
append_checklist_to_epic "$E_M2_E3" "$I_TEST1" "$I_CNTR1" "$I_PERF1"

########################################
# M3 — Engineering Deep Pack
########################################
M3_TITLE="$(ensure_milestone "M3 — Engineering Deep Pack" "Deep docs, contracts, CI workflow; packager & validation.")"

E_M3_E1=$(ensure_issue "M3.E1 — Deep Docs & Contracts" "$(ml_body <<'TXT'
**Goal:** Render deep docs; generate schemas & CI workflow.

**Acceptance**
- JSON/YAML syntactically valid; schemas meta-validated; yamllint passes.
TXT
)" "milestone: M3,area: templates,type: epic" "$M3_TITLE")
I_AGENT5=$(ensure_issue "AGENT-5: Deep docs (PRD, threat model, a11y, obs, runbooks, SLOs, ADRs)" "$(ml_body <<'TXT'
**AC**
- StrictUndefined; complete sections.
TXT
)" "milestone: M3,area: agents,type: task" "$M3_TITLE")
I_AGENT6=$(ensure_issue "AGENT-6: Generate ci/workflow.yml & contracts/*.schema.json" "$(ml_body <<'TXT'
**AC**
- Valid YAML/JSON; workflow parses.
TXT
)" "milestone: M3,area: ci,type: task" "$M3_TITLE")
append_checklist_to_epic "$E_M3_E1" "$I_AGENT5" "$I_AGENT6"

E_M3_E2=$(ensure_issue "M3.E2 — Packager & Manifest Integrity" "$(ml_body <<'TXT'
**Goal:** Zips & manifest with SHA-256, template metadata.

**Acceptance**
- All artifacts listed with {purpose, pack, sha256, template_*}.
TXT
)" "milestone: M3,area: core,type: epic" "$M3_TITLE")
I_PKG1=$(ensure_issue "PKG-1: PackagerAgent produces zips" "$(ml_body <<'TXT'
**AC**
- One zip per pack; reproducible filenames.
TXT
)" "milestone: M3,area: core,type: task" "$M3_TITLE")
I_PKG2=$(ensure_issue "PKG-2: Manifest sha256 & completeness check" "$(ml_body <<'TXT'
**AC**
- Hashes verified in CI; all files present.
TXT
)" "milestone: M3,area: ci,type: task" "$M3_TITLE")
append_checklist_to_epic "$E_M3_E2" "$I_PKG1" "$I_PKG2"

E_M3_E3=$(ensure_issue "M3.E3 — Output Validation in CI" "$(ml_body <<'TXT'
**Goal:** Validate all rendered contracts & workflow in CI.

**Acceptance**
- Deep E2E passes on OS matrix; all validations green.
TXT
)" "milestone: M3,area: ci,type: epic" "$M3_TITLE")
I_VALID1=$(ensure_issue "VALID-1: CI validates JSON/YAML & workflow" "$(ml_body <<'TXT'
**AC**
- jsonschema + yamllint + gh workflow parse.
TXT
)" "milestone: M3,area: ci,type: task" "$M3_TITLE")
I_TEST2=$(ensure_issue "TEST-2: Deep Pack E2E & schema contract tests" "$(ml_body <<'TXT'
**AC**
- Schemas valid against meta-schema; failures block.
TXT
)" "milestone: M3,area: ci,type: task" "$M3_TITLE")
append_checklist_to_epic "$E_M3_E3" "$I_VALID1" "$I_TEST2"

########################################
# M4 — Librarian & RAG (optional)
########################################
M4_TITLE="$(ensure_milestone "M4 — Librarian & RAG (optional)" "Opt-in research with provenance; PRD Evidence section.")"

E_M4_E1=$(ensure_issue "M4.E1 — Librarian & Stores" "$(ml_body <<'TXT'
**Goal:** Fetch, clean, embed content locally with provenance.

**Acceptance**
- LanceDB/Qdrant stores embeddings; provenance recorded.
TXT
)" "milestone: M4,area: agents,type: epic" "$M4_TITLE")
I_LIB1=$(ensure_issue "LIB-1: LibrarianAgent + BrowserAdapter (Playwright)" "$(ml_body <<'TXT'
**AC**
- Fetch & clean text; basic error handling.
TXT
)" "milestone: M4,area: agents,type: task" "$M4_TITLE")
I_LIB2=$(ensure_issue "LIB-2: VectorStoreAdapter (bge-small + LanceDB/Qdrant)" "$(ml_body <<'TXT'
**AC**
- Index & search APIs tested.
TXT
)" "milestone: M4,area: core,type: task" "$M4_TITLE")
I_LIB3=$(ensure_issue "LIB-3: Provenance model {source_url, retrieved_at, chunk_id}" "$(ml_body <<'TXT'
**AC**
- Persisted alongside embeddings.
TXT
)" "milestone: M4,area: schema,type: task" "$M4_TITLE")
append_checklist_to_epic "$E_M4_E1" "$I_LIB1" "$I_LIB2" "$I_LIB3"

E_M4_E2=$(ensure_issue "M4.E2 — RAG Integration & Guards" "$(ml_body <<'TXT'
**Goal:** PRD Evidence; offline enforcement; robots.txt respect.

**Acceptance**
- --research populates Evidence with citations; offline mode emits none and blocks sockets.
TXT
)" "milestone: M4,area: security,type: epic" "$M4_TITLE")
I_RAG1=$(ensure_issue "RAG-1: Integrate retrieval into PRD Evidence" "$(ml_body <<'TXT'
**AC**
- Relevant snippets + source URLs.
TXT
)" "milestone: M4,area: agents,type: task" "$M4_TITLE")
I_GUARD1=$(ensure_issue "GUARD-1: Offline mode blocks network in tests" "$(ml_body <<'TXT'
**AC**
- Socket monkeypatch; any HTTP call fails run.
TXT
)" "milestone: M4,area: security,type: task" "$M4_TITLE")
I_GUARD2=$(ensure_issue "GUARD-2: Max tokens per doc; robots.txt respect" "$(ml_body <<'TXT'
**AC**
- Configurable caps; compliance test.
TXT
)" "milestone: M4,area: security,type: task" "$M4_TITLE")
append_checklist_to_epic "$E_M4_E2" "$I_RAG1" "$I_GUARD1" "$I_GUARD2"

########################################
# M5 — Hardening & DX polish
########################################
M5_TITLE="$(ensure_milestone "M5 — Hardening & DX polish" "Resilience, usability, dev experience; mutation/property/golden tests.")"

E_M5_E1=$(ensure_issue "M5.E1 — CLI UX & Dry-Run" "$(ml_body <<'TXT'
**Goal:** Great DX flags & helpful errors; dry-run preview.

**Acceptance**
- Clear help; dry-run lists artifacts & diffs vs last run.
TXT
)" "milestone: M5,area: cli,type: epic" "$M5_TITLE")
I_DX1=$(ensure_issue "DX-1: Flags (--dials, --offline, --dry-run)" "$(ml_body <<'TXT'
**AC**
- Validated & documented; examples in README.
TXT
)" "milestone: M5,area: cli,type: task" "$M5_TITLE")
I_DX2=$(ensure_issue "DX-2: Friendly error messages with JSON pointers" "$(ml_body <<'TXT'
**AC**
- Clear remediation tips printed.
TXT
)" "milestone: M5,area: cli,type: task" "$M5_TITLE")
I_DX3=$(ensure_issue "DX-3: Dry-run preview of artifacts & diffs" "$(ml_body <<'TXT'
**AC**
- Shows planned outputs & changed files only.
TXT
)" "milestone: M5,area: cli,type: task" "$M5_TITLE")
append_checklist_to_epic "$E_M5_E1" "$I_DX1" "$I_DX2" "$I_DX3"

E_M5_E2=$(ensure_issue "M5.E2 — Advanced Quality Checks" "$(ml_body <<'TXT'
**Goal:** Mutation ≥70% on targeted modules; property & golden tests.

**Acceptance**
- Mutation targets hit; property tests pass; goldens stable.
TXT
)" "milestone: M5,area: ci,type: epic" "$M5_TITLE")
I_MUT1=$(ensure_issue "MUT-1: Mutation tests (mutmut) for core mapping" "$(ml_body <<'TXT'
**AC**
- Modules: SpecBuilder, rename/tag/link selection.
TXT
)" "milestone: M5,area: ci,type: task" "$M5_TITLE")
I_PROP1=$(ensure_issue "PROP-1: Property tests (hypothesis) for idempotency" "$(ml_body <<'TXT'
**AC**
- For any valid spec, rerun yields byte-identical outputs.
TXT
)" "milestone: M5,area: perf,type: task" "$M5_TITLE")
I_GOLD1=$(ensure_issue "GOLD-1: Golden tests for key templates" "$(ml_body <<'TXT'
**AC**
- Regen via 'make goldens-regen' only.
TXT
)" "milestone: M5,area: templates,type: task" "$M5_TITLE")
append_checklist_to_epic "$E_M5_E2" "$I_MUT1" "$I_PROP1" "$I_GOLD1"

E_M5_E3=$(ensure_issue "M5.E3 — Docs & Troubleshooting" "$(ml_body <<'TXT'
**Goal:** Troubleshooting, template changelog, spec migration docs.

**Acceptance**
- Dev can resolve common failures <10 minutes using docs.
TXT
)" "milestone: M5,area: docs,type: epic" "$M5_TITLE")
I_DOC1=$(ensure_issue "DOC-1: Troubleshooting guide" "$(ml_body <<'TXT'
**AC**
- Covers schema fails, Mermaid, path issues.
TXT
)" "milestone: M5,area: docs,type: task" "$M5_TITLE")
I_DOC2=$(ensure_issue "DOC-2: Template changelog & versioning policy" "$(ml_body <<'TXT'
**AC**
- Breaking changes require semver bump + notes.
TXT
)" "milestone: M5,area: docs,type: task" "$M5_TITLE")
I_DOC3=$(ensure_issue "DOC-3: Spec migration policy & 'migrate' usage" "$(ml_body <<'TXT'
**AC**
- Examples for upgrading specs; tests referenced.
TXT
)" "milestone: M5,area: docs,type: task" "$M5_TITLE")
append_checklist_to_epic "$E_M5_E3" "$I_DOC1" "$I_DOC2" "$I_DOC3"

green "All done (or previewed). Repo: $REPO"
