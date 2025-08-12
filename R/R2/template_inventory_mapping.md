# R2 — Template Inventory & Field Mapping

This maps **Source Spec** fields to templates for each pack.

## Balanced Pack
- **brief.md.j2**
  - meta.project_name → H1
  - problem.statement → Problem
  - problem.target_users → Audience
  - problem.value_hypothesis → Value Hypothesis
  - problem.non_goals → Non-Goals
  - success_metrics.business_kpis, ux_metrics → Success Metrics
  - risks_open_questions.risks → Risks
  - roadmap_preferences.milestone_length_weeks → Timeline hints
- **prd.md.j2**
  - goals from problem/value + constraints
  - functional requirements from diagram_scope + contracts_data.api_style
  - NFRs from success_metrics.nfr_budgets
  - AC from test_strategy.bdd_journeys
  - Open Questions from risks_open_questions.open_questions
- **test_plan.md.j2**
  - BDD from test_strategy.bdd_journeys
  - Contract targets from test_strategy.contract_targets
  - Property tests from test_strategy.property_invariants
  - Perf/mutation targets from test_strategy.performance_budgets / mutation_target_pct
- **roadmap.md.j2**
  - Milestone length & cadence from roadmap_preferences
  - Exit criteria wired to AC/NFRs
- **diagrams/lifecycle.mmd.j2**
  - Stages from diagram_scope.sequence_diagrams
- **diagrams/sequence_*.mmd.j2**
  - From diagram_scope.user_flows

## Engineering Deep Pack
- **docs/prd_engineering_deep.md.j2**
  - Deep FR/NFR sections as above + operations.slos, observability, ADR seeds
- **docs/threat_model.md.j2**
  - compliance_context, operations, risks
- **docs/accessibility.md.j2**
  - compliance_context.accessibility_targets + docs/CLI notes
- **docs/observability.md.j2**
  - operations.observability + analytics.kpis
- **docs/runbooks.md.j2**
  - operations.ci_cd + recovery steps
- **docs/slos.md.j2**
  - operations.slos
- **contracts/*.schema.json.j2**
  - contracts_data.* sections
- **ci/workflow.yml.j2**
  - operations.ci_cd.stages/quality_gates
- **tests/bdd/core.feature.j2**
  - test_strategy.bdd_journeys

## Template Variables (common)
- `today`, `generated_at`, `template_version`, `spec_version`, `run_id`
