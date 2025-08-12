# R3 — Acceptance Tests (End-to-End)

## Fixtures
- **idea_card.md** — sample idea with Problem/Audience/Value/Non-goals
- **decision_sheet.md** — chosen dials and constraints
- **taxonomy.md** — tags and folder rules (optional)
- **small_vault/** — 30–50 tiny notes for link/tag checks

## Scenarios
1. **Balanced Pack from Idea Card**
   - Input: idea_card.md + decision_sheet.md (Balanced, Dual-Track)
   - Expect: brief.md, prd.md, test_plan.md, roadmap.md, lifecycle + 1 sequence diagram
   - Check: docs compile; Mermaid passes linter; sections not empty

2. **Engineering Deep Pack**
   - Input: same, pack=deep
   - Expect: deep PRD, contracts, CI, threat model, accessibility, observability, runbooks, SLOs, BDD feature
   - Check: JSON Schemas valid; YAML parses; required sections present

3. **Idempotent Re-run**
   - Run #1 then Run #2 with same inputs
   - Expect: zero diffs in artifacts (ignoring timestamps/hash)

4. **Offline Mode**
   - Flag: `--offline`
   - Expect: no network calls; Librarian skipped; packs still render

5. **Failing Validation**
   - Spec with invalid nfr_budgets (negative latency)
   - Expect: exit code 2; error details with JSON pointer paths

6. **Performance Budget**
   - Warm cache; measure render end-to-end
   - Expect: p95 ≤ 8s on dev machine

## Metrics we record per test
- render_duration_ms, artifacts_count, schema_errors, mermaid_valid
