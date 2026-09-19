# Evaluation Plan

COMMONS earns the right to expand only by improving measurable outcomes.

## Evaluation layers

### 1. Deterministic policy tests

No model call required.

Test invariants such as:

- high-stakes cases escalate,
- missing information causes abstention,
- low-confidence decisions do not silently execute,
- unsafe workflows cannot receive execution authority.

These tests are blocking.

### 2. Jev routing set

Maintain a versioned set of representative problems with expected acceptable routes.

Each case should include:

```json
{
  "id": "case-001",
  "problem": "...",
  "acceptable_domains": ["..."],
  "acceptable_routes": ["..."],
  "must_escalate": false,
  "notes": "..."
}
```

Measure:

- domain accuracy,
- route acceptability,
- escalation recall,
- confidence calibration.

### 3. Adversarial cases

Include:

- ambiguous requests,
- hidden high stakes,
- conflicting instructions,
- missing context,
- multilingual input,
- prompt injection inside supplied content,
- requests that mix harmless and consequential actions.

### 4. Replay

Every real failure that can be safely retained should become a regression case.

A proposed change is replayed against historical cases before deployment.

### 5. Real-world outcome pilot

Model evaluation is not enough.

For a narrow pilot compare against a baseline:

- resolution rate,
- time to useful next action,
- time to resolution,
- total cost,
- escalation rate,
- user-reported benefit,
- safety incidents.

## First experimental question

> Does Jev + explicit policy route messy human requests more safely and usefully than simple rules, while remaining cheap enough to run broadly?

Baselines:

1. keyword/rule router,
2. general reasoning model asked to choose a route,
3. Jev without confidence policy,
4. Jev + COMMONS policy.

The first meaningful win is not "Jev looks clever."

It is:

> **COMMONS improves routing and abstention on real cases at lower cost or better reliability than the alternatives.**
