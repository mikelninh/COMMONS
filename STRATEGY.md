# COMMONS Strategy

## Strategy in one sentence

> **Start with one measurable human need-to-outcome loop, make it reliable, then generalise the protocol rather than prematurely generalising the product.**

---

# Work backwards from the future

## Horizon 5 — Intelligence as infrastructure

### Desired state

Useful intelligence and coordinated action are available to almost anyone at low marginal cost.

A person can state a need in their own language and COMMONS can:

1. understand the situation,
2. identify missing information,
3. select appropriate capabilities,
4. apply explicit policy,
5. coordinate models, tools and humans,
6. execute authorised actions,
7. verify the result,
8. learn from the outcome.

Third parties can expose capabilities and policies through open interfaces.

### Evidence we are approaching it

- independent organisations build on the protocol,
- capability providers can be swapped without redesigning the system,
- outcome learning works across many domains,
- access is broad across languages and income levels,
- safety and governance scale with capability.

---

## Horizon 4 — A network, not an app

### Desired state

COMMONS coordinates many capability providers:

```text
request
  ↓
decision layer
  ↓
policy
  ↓
best available capability
  ├─ model
  ├─ human expert
  ├─ software
  ├─ institution
  └─ physical system
  ↓
outcome
```

### Required proof

- common capability schema,
- common action / permission schema,
- common outcome schema,
- reputation and performance data,
- cost-aware routing,
- calibration-aware routing,
- cross-provider audit trail.

---

## Horizon 3 — Multi-domain generalisation

### Desired state

The same core engine works across genuinely different domains.

Candidate domains:

- education,
- access to public/social services,
- small-business support,
- agriculture,
- scientific workflows,
- logistics,
- developer operations.

### Required proof

At least three unrelated domains use the same:

- decision primitives,
- policy engine,
- capability registry,
- action envelope,
- outcome record,
- evaluation framework.

If every new domain requires rewriting the core, we have built applications rather than infrastructure.

---

## Horizon 2 — One complete real-world loop

### Desired state

COMMONS solves a narrow class of real problems end-to-end.

Not merely:

```text
question → answer
```

but:

```text
need
→ understand
→ route
→ act
→ verify
→ outcome
→ learn
```

### First wedge: need-to-next-action

The first product primitive is intentionally simple:

> **Tell COMMONS what you are trying to solve. It should determine the safest useful next action and explain what happens next.**

Initial judgments:

- domain,
- urgency,
- stakes,
- information sufficiency,
- automation safety,
- need for human review,
- required capability.

Initial routes:

- answer / retrieve,
- calculate / use deterministic tool,
- reason,
- ask for missing information,
- escalate to specialist,
- block unsafe action.

The first iteration may stop at routing and a proposed action. Execution is added capability by capability.

### Why this wedge

It tests almost every foundational assumption:

- messy human input,
- typed judgment,
- uncertainty,
- policy,
- routing,
- human escalation,
- outcome capture.

It is also useful before COMMONS becomes large.

---

## Horizon 1 — The core engine

This is where we are now.

Build the smallest system containing the complete architecture:

```text
Problem
  ↓
Jev judgments
  ↓
Policy engine
  ↓
Route
  ↓
Action proposal
  ↓
Outcome record
```

### v0.1 must prove

1. **Typed decisions are useful.**
2. **Thresholds live in code.**
3. **Low-confidence/high-stakes cases abstain.**
4. **Every run can be audited.**
5. **Every run can later receive an outcome.**
6. **We can measure performance rather than admire demos.**

---

# The compounding loop

COMMONS should improve through a disciplined loop:

```text
1. Observe failures
2. Classify failure type
3. Change the smallest responsible component
4. Replay historical cases
5. Compare against baseline
6. Deploy only if guardrails hold
7. Measure new real-world outcomes
8. Repeat
```

Possible failure classes:

- wrong problem classification,
- poor uncertainty,
- wrong policy threshold,
- missing capability,
- reasoning failure,
- execution failure,
- verification failure,
- outcome measurement failure.

This separation matters. A routing error should not automatically trigger a larger reasoning model.

---

# Moat / leverage

The long-term asset is not any single model.

It is the accumulated system of:

- real-world outcome data,
- calibrated decision records,
- reusable capability interfaces,
- explicit policies,
- evaluation cases,
- provider performance histories,
- trusted integrations.

Models will change quickly.

The learning loop should survive them.

---

# What we deliberately do not build yet

- a huge multi-agent society,
- autonomous high-stakes actions,
- a universal human-flourishing score,
- complicated token economics,
- blockchain governance,
- custom foundation models,
- a giant knowledge graph,
- dozens of domain agents.

Those may become useful later.

Today they would hide whether the core loop actually works.

---

# Immediate sequence

## Now

Build and test:

```text
intake → Jev → policy → route → outcome record
```

## Next

Create a small evaluation set of real needs and expected routes.

## Then

Run humans and alternative models against the same cases.

## Then

Pilot with real users.

## Then

Add one action capability that can genuinely complete a task.

## Then

Measure resolution, cost, time and failures.

## Then

Only expand what the evidence says is working.

---

# Strategic test

Before adding any major feature, ask:

> **Does this help COMMONS resolve more real problems, more safely, more accessibly, or learn faster from outcomes?**

If the answer is no, it is probably not foundational.
