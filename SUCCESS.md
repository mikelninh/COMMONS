# COMMONS Success

## The primary metric

> **Problems measurably resolved per unit of intelligence cost.**

This is intentionally outcome-oriented.

COMMONS should not optimise for:

- messages sent,
- time in app,
- agent steps,
- tokens consumed,
- model sophistication,
- engagement,
- number of generated plans.

Those can be diagnostic metrics, never the mission.

---

# What counts as a resolved problem?

A case is resolved when:

1. the user or affected system had a concrete desired outcome,
2. COMMONS contributed to an action or decision,
3. there is evidence of the resulting state,
4. the outcome satisfies explicit resolution criteria.

Examples:

- an eligible benefit was successfully accessed,
- a learner can correctly perform the target skill,
- a bug was fixed and tests pass,
- a service appointment was successfully booked,
- a logistics exception was cleared,
- an experiment discriminated between competing hypotheses.

For subjective goals, the user's own evaluation matters, but should not be the only signal when objective verification is available.

---

# Metric tree

## Outcome

- resolution rate
- partial resolution rate
- recurrence rate
- user-reported benefit
- objective verification rate

## Speed

- time to first useful action
- time to resolution
- number of handoffs

## Cost

- model cost
- human review cost
- tool / execution cost
- total cost per resolved case

## Decision quality

- classification accuracy
- calibration error
- confidence / accuracy curve
- abstention quality
- routing regret: how much worse was the chosen route than the best known route?

## Safety

- harmful action rate
- unauthorised action attempts
- false-safe rate
- false-escalation rate
- reversibility / recovery success
- audit completeness

## Access

- supported languages
- completion by language
- performance gaps across user groups where ethically and legally measurable
- cost to user
- accessibility performance
- low-bandwidth / low-compute usability

## Agency

We do not compress agency into one score, but can ask whether users leave the interaction with:

- greater understanding,
- clearer options,
- meaningful choice,
- ability to act without COMMONS next time,
- appropriate control over data and actions.

---

# Calibration is foundational

If COMMONS says an event is 80% likely, events in that class should occur approximately 80% of the time.

We will track calibration separately for:

- domains,
- question types,
- stakes,
- languages,
- models / versions.

High average accuracy with bad calibration is dangerous because it makes escalation policy unreliable.

---

# Stage gates

These are engineering targets, not claims about the future.

## Gate 0 — It runs

- one CLI/API request completes,
- Jev produces typed judgments,
- policy returns a route,
- an auditable decision record is created,
- an outcome can later be attached.

## Gate 1 — It beats trivial routing

On a labelled evaluation set:

- materially outperform simple keyword/rule baselines,
- confidence is useful for separating easy and hard cases,
- high-stakes cases reliably escalate under policy.

## Gate 2 — It helps real people

In a narrow pilot:

- users reach useful next actions more often than the baseline,
- measurable time-to-resolution improves,
- users understand when and why COMMONS escalates,
- no serious safety failures.

## Gate 3 — It closes tasks

At least one capability moves from recommendation to authorised execution and verification.

The key measure becomes **verified resolution**, not recommendation quality.

## Gate 4 — It generalises

Three meaningfully different domains use the same core interfaces without core rewrites.

## Gate 5 — Others build on it

External developers or organisations can register capabilities, policies or evaluators and get measurable value.

## Gate 6 — Public-good scale

COMMONS can deliver high-quality assistance at very low marginal cost across languages and regions while preserving safety, agency and measurable outcomes.

---

# Ultimate success

We should consider COMMONS a genuine success when the following statement is empirically true:

> **For many important classes of human problems, access to high-quality understanding and coordinated help is no longer primarily limited by money, language, location or knowledge of which institution to ask — and the system can demonstrate from outcomes that it helps without quietly taking agency away.**

That is far beyond v0.1.

Every version should nevertheless move measurably toward it.
