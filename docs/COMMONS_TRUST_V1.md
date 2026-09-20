# COMMONS TRUST v1

## Purpose

COMMONS should not ask people to trust it because it uses AI.

It should earn trust continuously by making claims, sources, uncertainty, authority and failures inspectable.

The v1 trust stack is:

**Claim Ledger → Source Registry → Evaluation Lab → Action Safety → Incident / Correction Log**

The public website exposes the same trust registry that CI evaluates.

## Reliability constitution

1. Never fabricate reality.
2. Separate observation, derivation, inference and proposal.
3. Preserve provenance.
4. Preserve uncertainty.
5. Never imply causality without evidence.
6. Human authority scales with consequence.
7. Prefer reversible actions.
8. Fail visibly and safely.
9. Record what happened.
10. Measure outcomes, not activity.
11. Correct material mistakes publicly.
12. Optimize for human agency, not dependence.

## Canonical trust registry

The machine-readable source of truth is:

`public/trust-registry.json`

It contains:

- source registry
- claim ledger
- freshness windows
- claim types
- limitations
- conflicts
- incidents
- capability levels
- required evaluations
- correction policy

## Claim types

### observed
Directly reported by a named source or dataset.

### derived
Deterministically calculated from sourced observations.

### inferred
Interpretation or model-produced conclusion.

### proposed
Possible intervention or action, not a statement of reality.

The UI must never collapse these into one visual category.

## Freshness

High-criticality claims can declare a freshness window.

If the current time moves beyond that window, COMMONS evaluates the trust state as **DEGRADED**.

This means trust can decay automatically even if nobody edits the page.

Example:

- WHO DRC emergency counts
- as of 16 Sep 2026
- 7-day freshness window

The trust evaluator becomes degraded once those figures are older than the declared window.

## Source registry

Every source records:

- organization
- role / class
- domain
- URL
- update pattern
- known limitations

A source cannot be considered complete if its limitations are missing.

## Trust status

The current site can show **HEALTHY** only when required conditions pass.

At minimum:

- 100% active claims have registered provenance
- no active critical claim is stale
- no referenced source is missing
- no unresolved conflict is hidden
- no open high-severity trust incident exists
- required evaluations pass

If the trust registry fails to load, the product enters **DEGRADED** mode.

## Action safety

COMMONS currently enables:

- L0 — observe
- L1 — explain
- L2 — propose
- L3 — prepare / hand off

It keeps disabled:

- L4 — execute reversible actions through integrations
- L5 — execute consequential actions

The model does not acquire authority merely because it becomes more capable.

### Trust-gated direct action

A direct external action can be blocked if:

- the trust registry is unavailable
- a high-severity trust incident is open
- a critical claim for that story is stale
- a source reference for that story is missing

This is intentional friction.

## Action receipts

Action Loop v1 can record local receipts.

External completion is never silently verified.

A user can explicitly self-report an external action as completed, but the receipt remains labeled:

**Self-reported by you**

Later outcome evidence can be described as:

**evidence after your action**

but never:

**evidence caused by your action**

without causal evidence.

## Evaluation lab

The browser evaluator checks:

- provenance coverage
- critical freshness
- source integrity
- conflict safety
- incident safety
- claim taxonomy
- action causality constraints
- external action verification disclosure
- no-invented-action safety state
- degraded-mode behavior

CI independently evaluates the public registry in Python.

The release test also advances the clock beyond a critical freshness window and requires the status to flip from **HEALTHY** to **DEGRADED**.

## Incidents and corrections

Trust is not the absence of mistakes.

Material failures should preserve:

- what happened
- impact
- root cause
- correction
- prevention
- timestamps
- resolution status

The current public incident log includes the 19 Sep 2026 CSS containment regression that exposed inactive UI layers.

That incident is preserved as resolved instead of deleted from history.

## Current limits

TRUST v1 does not yet provide:

- cryptographically signed source attestations
- independent third-party audit
- server-side append-only incident history
- organization-grade permissions
- verified payment receipts
- automatic contradiction discovery across the open web
- background monitoring of all source freshness
- independent causal evaluation of interventions

These are future trust layers, not UI details.

## Local evaluation

Run:

```bash
python scripts/trust_report.py
```

or evaluate the registry directly in Python:

```python
from commons.trust import load_registry, evaluate_registry

registry = load_registry("public/trust-registry.json")
report = evaluate_registry(registry)
print(report["status"])
```
