# R4 — Repo Scaffold Plan

## Structure
```
spec-to-pack-studio/
  src/
    studio/
      cli.py
      api.py
      spec_builder.py
      agents/
        framer.py
        librarian.py
        slicer.py
        prd_writer.py
        diagrammer.py
        qa_architect.py
        roadmapper.py
        critic.py
      adapters/
        llm.py
        vectors.py
        browser.py
        templates.py
      templates/
        balanced/
          brief.md.j2
          prd.md.j2
          test_plan.md.j2
          roadmap.md.j2
          diagrams/
            lifecycle.mmd.j2
            sequence_ingest.mmd.j2
        deep/
          docs/
            prd_engineering_deep.md.j2
            threat_model.md.j2
            accessibility.md.j2
            observability.md.j2
            runbooks.md.j2
            slos.md.j2
            adr_index.md.j2
            adr/ADR-0001.md.j2
          contracts/
            config.schema.json.j2
            pipeline_event.schema.json.j2
            note_metadata.schema.json.j2
          ci/workflow.yml.j2
          tests/bdd/core.feature.j2
  tests/
    unit/
    contract/
    e2e/
    property/
  fixtures/
    idea_card.md
    decision_sheet.md
    taxonomy.md
    small_vault/
  schemas/
    source_spec.schema.json
    artifact_index.schema.json
  ci/
    workflow.yml
  .pre-commit-config.yaml
  pyproject.toml
  README.md
  LICENSE
```

## Make/Tasks
- `make install` — create venv, install deps
- `make lint` — ruff/black/isort
- `make test` — pytest all
- `make e2e` — run acceptance tests
- `make gen` — run `studiogen generate ...`
- `make package` — zip outputs

## Branching & Release
- trunk-based, PRs for features; tags `v0.x.y`
- template versions pinned; changelog per template set

## Pre-commit Hooks
- ruff, black, isort, yamllint, jsonschema validation for templates
