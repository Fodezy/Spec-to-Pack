# {{ meta.name }}

**Version:** {{ meta.version }}
{% if meta.description %}
**Description:** {{ meta.description }}
{% endif %}

## Problem Statement

{{ problem.statement }}

{% if problem.context %}
### Context

{{ problem.context }}
{% endif %}

## Success Metrics

{% if success_metrics.metrics %}
{% for metric in success_metrics.metrics %}
- {{ metric }}
{% endfor %}
{% else %}
- _No success metrics defined_
{% endif %}

## Constraints

- **Offline Mode:** {{ "Yes" if constraints.offline_ok else "No" }}
- **Budget:** {{ constraints.budget_tokens }} tokens
- **Duration:** {{ constraints.max_duration_minutes }} minutes

## Configuration

- **Audience:** {{ dials.audience_mode.value }}
- **Development Flow:** {{ dials.development_flow.value }}
- **Test Depth:** {{ dials.test_depth.value }}

---

*Generated with Spec-to-Pack Studio*
*Template: balanced-1.0.0*