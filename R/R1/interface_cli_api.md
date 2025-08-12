# R1 — Interface Contracts (CLI & API)
**Date:** 2025-08-12

This document specifies the CLI surface and an optional HTTP API. Both operate on the **Source Spec** JSON and produce artifact packs.

## CLI
### Commands
- `studiogen validate --spec path/to/spec.json`
- `studiogen generate --idea path/to/idea.md --decisions path/to/decision.md [--dials audience=Balanced,flow=Dual-Track] -o out/`
- `studiogen render --spec path/to/spec.json --pack balanced|deep|both -o out/ [--offline]`
- `studiogen package --dir out/ --zip out/bundle.zip`
- `studiogen dry-run --idea path/to/idea.md -o out/`
- `studiogen init` (creates templates & example spec in current repo)

### Global Flags
- `--offline` (default true): disallow network during generation.
- `--research` (explicit): permit web research (Librarian).
- `--format md|json|yaml` (default md for docs).
- `--verbose` / `--quiet`

### Exit Codes
- `0` success · `2` validation error · `3` generation error · `4` render error

## HTTP API (optional)
Base: `/api/v1`

### POST /generate
Request:
```json
{
  "idea_card": "string-or-markdown",
  "decision_sheet": "string-or-markdown",
  "dials": {"audience_mode":"Balanced","development_flow":"Dual-Track","test_depth":"Pyramid"},
  "pack": "balanced|deep|both",
  "offline": true
}
```
Response:
```json
{"run_id":"uuid","spec_path":"/runs/123/spec.json","artifacts":[{"name":"brief.md","path":"/runs/123/brief.md"}]}
```

### POST /validate
- Body: `spec` (JSON).  
- Response: list of schema errors (empty if valid).

### GET /runs/{id}/index
- Returns artifact manifest (see artifact_index schema).

### Errors
- JSON:
```json
{"error":"ValidationError","message":"latency_p95_ms must be > 0","details":[...]}
```

## Artifacts & Manifest
Every run emits `artifact_index.json`:
```json
{
  "run_id":"uuid",
  "generated_at":"ISO-8601",
  "artifacts":[
    {"name":"brief.md","purpose":"Stakeholder Brief","pack":"balanced","path":"./brief.md"},
    {"name":"prd_engineering_deep.md","purpose":"Deep PRD","pack":"deep","path":"./docs/prd_engineering_deep.md"}
  ]
}
```
