# Spec-to-Pack Studio

Generate high-quality engineering document **packs** from a structured product **spec**. Feed it an Idea + Decisions (or a Source Spec), and it will validate, orchestrate agents, render templates, and emit a consistent artifact set (e.g., PRD, Test Plan, diagrams, roadmaps) along with a machine-readable manifest.

> Status: **Active Development** | **M3 Complete** - Deep pack generation with contracts, CI workflows, and security documentation now available.

---


## Why

Teams waste time rewriting the same docs in different formats. Spec-to-Pack Studio turns a single structured spec into repeatable, validated outputs with:

* **Strong schemas** (JSON Schema 2020-12) for specs and manifests
* **Determinism** (idempotent reruns, golden tests)
* **Clear governance** (template sets with semver, contract checks)
* **Good DX** (helpful CLI, dry-run, audit logs)

---

## What it produces

Transform your project ideas into comprehensive documentation packs:

### **🎯 Balanced Pack** - *Business-Ready Documentation*
* **Product Requirements Document (PRD)** - Detailed requirements with your actual project context
* **Test Plan** - Comprehensive testing strategy with QA enhancements  
* **Project Roadmap** - Timeline and milestone planning
* **System Diagrams** - E-commerce specific lifecycle and sequence diagrams
* **Project Brief** - Executive summary and overview

### **⚡ Deep Pack** - *Engineering-Grade Documentation*
* **Security Documentation** - STRIDE threat models with risk assessments
* **Service Level Objectives (SLOs)** - Performance targets with error budget policies
* **CI/CD Pipeline** - Production-ready GitHub Actions workflow with security scanning
* **Contract Schemas** - API, data, and service contract definitions (JSON Schema 2020-12)
* **ZIP Bundle** - Complete package with integrity manifest

### **📊 Output Quality**
All outputs are:
* **Personalized** - Generated from your actual idea.yaml content, not generic templates
* **Production-Ready** - Professional quality documentation suitable for enterprise projects
* **Auditable** - Complete artifact tracking in `artifact_index.json` with SHA-256 hashes
* **Deterministic** - Identical outputs for identical inputs (except timestamps)

---

## Quick Start

### **Installation**
```bash
git clone https://github.com/Fodezy/Spec-to-Pack.git
cd Spec-to-Pack
pip install -e ".[dev]"
```

### **Generate Your First Pack**
```bash
# Create your idea file
cat > idea.yaml << 'EOF'
name: "E-Commerce Platform"
description: "Modern e-commerce solution with user management and payment processing"
problem_statement: "Small businesses need affordable, scalable e-commerce solutions"
target_audience: "Small to medium business owners"
key_features:
  - "User registration and authentication"
  - "Product catalog with search"
  - "Shopping cart and checkout"
  - "Payment processing"
  - "Admin dashboard"
EOF

# Create decisions file
cat > decisions.yaml << 'EOF'
dials:
  audience_mode: "business"
  development_flow: "agile"  
  test_depth: "comprehensive"
EOF

# Generate business documentation
python -m studio.cli generate \
  --idea idea.yaml \
  --decisions decisions.yaml \
  --pack balanced \
  --out ./output

# Generate engineering documentation  
python -m studio.cli generate \
  --idea idea.yaml \
  --decisions decisions.yaml \
  --pack deep \
  --out ./output_deep
```

### **Available Commands**
```bash
# Validate your input files
python -m studio.cli validate path/to/spec.yaml

# Generate specific pack types
python -m studio.cli generate --pack balanced  # Business docs
python -m studio.cli generate --pack deep      # Engineering docs  
python -m studio.cli generate --pack both      # Everything

# Use offline mode (no network access)
python -m studio.cli generate --offline --out ./output
```

---

## Example Output Structure

After running generation, you'll get organized documentation:

### **Balanced Pack Output**
```
output/
├── artifact_index.json      # Manifest with SHA-256 hashes
├── brief.md                 # Project overview
├── prd.md                   # Product Requirements Document
├── test_plan.md            # Testing strategy (enhanced by QA Architect)
├── roadmap.md              # Project timeline and milestones
└── diagrams/
    ├── lifecycle.mmd       # E-commerce user journey flow
    └── sequence.mmd        # Customer→WebApp→API→Database interactions
```

### **Deep Pack Output**  
```
output_deep/
├── artifact_index.json          # Manifest with integrity tracking
├── threat_model.md              # STRIDE security analysis
├── slos.md                      # Service level objectives with error budgets
├── workflow.yml                 # GitHub Actions CI/CD pipeline
├── api_contract.schema.json     # API contract definitions
├── data_contract.schema.json    # Data schema contracts
├── service_contract.schema.json # Service level agreements
└── output_bundle.zip           # Complete packaged bundle
```

### **Project Architecture**
```
src/studio/
├── cli.py                       # CLI interface
├── app.py                       # Main application facade  
├── orchestrator.py              # Pipeline execution with budgets/timeouts
├── spec_builder.py              # Merge idea+decisions into SourceSpec
├── agents/                      # Content generation agents
│   └── base.py                  # All 13+ agents (Framer, PRDWriter, etc.)
├── templates/
│   ├── balanced/               # Business documentation templates
│   └── deep/                   # Engineering documentation templates
└── types.py                    # Core data models and enums
```

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

## Real-World Example

Here's what the E-commerce platform example generates:

### **PRD Extract** (`prd.md`)
```markdown
# Product Requirements Document: E-Commerce Platform

## Executive Summary
Small businesses need an affordable, scalable e-commerce solution that can handle 
product management, customer orders, and payment processing without requiring 
extensive technical expertise

### Context  
Small to medium business owners who want to sell products online

### Success Metrics
- User registration and authentication
- Product catalog with search and filtering  
- Shopping cart and checkout process
- Payment processing integration
- Admin dashboard for business owners
```

### **Threat Model Extract** (`threat_model.md`)
```markdown
## STRIDE Threat Categories

#### Information Disclosure - **Risk Level: High**
- **Threat:** Unauthorized access to customer payment data
- **Assets at Risk:** Credit card information, personal data, order history
- **Mitigations:**
  - PCI-DSS compliance with end-to-end encryption
  - Role-based access control for admin functions
  - Data masking in logs and non-production environments
```

### **SLO Extract** (`slos.md`)
```markdown
### 1. Availability SLO
**Target**: 99.9% (8.76 hours downtime per year)
**Error Budget**: 43.2 minutes per month

### 2. Payment Processing SLO  
**Availability**: 99.9%
**Latency**: P95 < 3000ms
**Error Rate**: < 0.2%
Higher latency tolerance due to external payment provider dependencies.
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

## Development Status & Roadmap

| Milestone                            | Status | Theme                    | Key Features                                                         |
| ------------------------------------ | ------ | ------------------------ | -------------------------------------------------------------------- |
| **M0 — Foundations & Schemas**       | ✅     | Scaffolding & validation | Repo layout, CI matrix, schemas, validator, fixtures               |
| **M1 — Spec Builder & Orchestrator** | ✅     | Merge/Frame + runtime    | SpecBuilder, Framer-lite, budgets/timeouts, audit                  |
| **M2 — Balanced Pack v1**            | ✅     | Agents + templates       | PRD/Test Plan/Diagrams/Roadmap, template harness, E2E & perf gates |
| **M3 — Engineering Deep Pack**       | ✅     | Deep docs & contracts    | Generated contracts, CI workflow, packager + manifest integrity    |
| **M4 — Librarian & RAG**             | 🔄     | Research w/ provenance   | LibrarianAgent, vector store, offline/robots guards                |
| **M5 — Hardening & DX**              | 📋     | Quality & usability      | Mutation/property/golden tests, CLI UX, troubleshooting docs       |

### **Recent Achievements (M3 Complete)**
- ✅ **Deep Pack Generation** - Professional-grade engineering documentation
- ✅ **Security Documentation** - STRIDE threat models with practical mitigations
- ✅ **SLO Framework** - Complete service level objectives with error budgets
- ✅ **CI/CD Pipelines** - Production-ready GitHub Actions workflows
- ✅ **Contract Schemas** - API, data, and service contract definitions
- ✅ **YAML Mapping Fixes** - User content now properly populates all templates
- ✅ **E-commerce Diagrams** - Realistic customer journey and system interactions

---

## Contributing

1. **Fork & branch**: `feat/*`, `fix/*`.
2. **Run checks**: `make test` (or `pytest`), `pre-commit run -a`.
3. **Add tests** for new behavior (schema, golden, E2E as appropriate).
4. **Open a PR** with a clear description and link to the tracked issue/epic.

Labels you’ll see: `type: epic`, `type: task`, `area:*`, and `milestone:*`.

---

## Troubleshooting

### **Common Issues**

**❌ "unacceptable character #x0000" in YAML files**
```bash
# Remove null characters from YAML files
tr -d '\000' < idea.yaml > idea_clean.yaml
mv idea_clean.yaml idea.yaml
```

**❌ Placeholder content instead of your data**
- Ensure field names match: `problem_statement` (not `problem`), `target_audience` (not `context`)
- Check nested structure: Use `dials:` section in decisions.yaml
- Verify enum values: `"business"` → `"balanced"`, `"comprehensive"` → `"full_matrix"`

**❌ Template generation errors**
```bash  
# Validate your YAML files first
python -c "import yaml; print(yaml.safe_load(open('idea.yaml')))"
python -c "import yaml; print(yaml.safe_load(open('decisions.yaml')))"
```

**❌ Missing output files**
- Check output directory permissions
- Ensure all required YAML fields are present
- Use `--offline` flag if network issues occur

### **Getting Help**
- Review the example files in the Quick Start section
- Check generated `audit.jsonl` for detailed execution logs
- Validate YAML structure matches the expected format

---

## License

See `LICENSE` in this repository.

---

## Acknowledgments

Built with a bias toward **clarity, contracts, and repeatability** so docs stay trustworthy — and engineers stay sane.
