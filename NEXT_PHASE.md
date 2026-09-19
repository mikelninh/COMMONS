# COMMONS Next Phase — v0.3

## Objective

Move from:

```text
problem → judgment → route
```

to:

```text
problem
→ judgment
→ evidence
→ capability
→ authorised action
→ verification
→ outcome
→ learning
```

The next phase is **Evidence + Capability Network**.

---

## 1. Evidence objects

COMMONS needs a reusable evidence schema:

```text
claim
source
retrieved_at
jurisdiction / scope
freshness
confidence
contradictions
provenance
```

For civic use, evidence must distinguish:

- law / official rule,
- administrative guidance,
- empirical data,
- stakeholder testimony,
- modelling / forecast,
- opinion or value judgment.

A policy decision should never silently turn a value judgment into a factual claim.

---

## 2. Capability registry

Every provider — AI, human, API, institution or later robot — should expose a capability manifest.

Minimum fields:

```text
id
description
accepted_input
possible_actions
required_permissions
risk_class
cost_model
reversibility
execution_method
verification_method
performance_history
```

This is the beginning of the **network of intelligence and capability**.

The router should eventually choose providers using observed performance, cost, latency, access and safety — not brand loyalty to one model.

---

## 3. Action envelopes

Do not jump from “advice” to “full autonomy”.

Use explicit authority levels:

1. **READ** — retrieve information.
2. **EXPLAIN** — analyse or translate.
3. **DRAFT** — prepare an action for approval.
4. **EXECUTE_REVERSIBLE** — perform a bounded reversible action with consent.
5. **EXECUTE_CONSEQUENTIAL** — requires stronger policy / accountable human approval.
6. **PROHIBITED** — action is outside COMMONS authority.

Every capability declares which level it requires.

---

## 4. Outcome loop

Every real case should support:

```text
desired outcome
baseline
action
result
verification
time
cost
benefit
agency
recurrence
failure reason
```

This is how COMMONS stops optimising demos and starts learning from reality.

---

# First two pilots

## Pilot A — Public-service access

A user can provide a confusing public-service problem or letter.

COMMONS should:

1. identify jurisdiction/process,
2. retrieve authoritative current information,
3. explain it in the user's language,
4. identify deadlines and missing information,
5. produce a concrete checklist,
6. draft the next message/form step,
7. ask for approval before any submission,
8. follow up on whether the issue was resolved.

Initial authority ceiling: **DRAFT**.

This is a good first real-world wedge because success can often be verified.

## Pilot B — Civic Decision Canvas

For citizens, officials and communities.

Input: a concrete public problem or policy proposal.

Output:

- decision being made,
- objective(s),
- affected groups,
- known evidence,
- missing evidence,
- uncertainties,
- implementation constraints,
- reversible experiments,
- measurable outcomes,
- consultation questions,
- strongest documented competing considerations.

The system does **not** select a political winner or tell citizens how to vote.

The proof of usefulness is whether it makes the process clearer, more evidence-aware, more inspectable and easier to act on.

---

# v0.3 stage gates

These are engineering targets to test, not claims that the system already meets them.

### Synthetic benchmark

- ≥90% acceptable routing on the maintained civic set,
- 0 policy-authority violations,
- <5% false-safe rate on labelled non-automatable cases,
- no unexplained >10 percentage-point route gap between supported languages.

### Real pilot

Collect at least 50 real cases across citizen/public-service/community use.

Track:

- useful-next-action rate,
- verified resolution rate,
- time-to-resolution,
- total intelligence + human cost,
- user-rated clarity,
- agency rating,
- escalation quality,
- recurrence,
- safety incidents.

Every meaningful failure becomes a regression case.

---

# What not to build yet

- automated political decisions,
- political persuasion or electoral recommendation,
- irreversible government actions,
- a giant multi-agent society,
- a universal “good policy” score,
- opaque optimisation of human preferences,
- dozens of integrations before one capability closes the loop.

The next phase wins if COMMONS becomes **measurably useful**, not merely more impressive.
