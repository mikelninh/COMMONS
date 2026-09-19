# COMMONS

> **Open intelligence infrastructure for turning human needs into accountable action — and learning from reality.**

COMMONS is an experimental open-source system for closing the loop:

```text
information → understanding → decision → coordination → execution → feedback
```

The long-term goal is not to build another chatbot. It is to make **useful intelligence broadly accessible** and capable of improving real outcomes while remaining observable, governable, reversible where possible, and subordinate to human-set values.

## North star

> **Give every person the greatest practical opportunity to live a healthy, free, meaningful and joyful life — by making trustworthy intelligence and coordinated action abundant.**

We operationalise that aspiration carefully. COMMONS does **not** collapse human flourishing into one score. It measures concrete outcomes such as resolution, access, time, cost, safety, agency, and recurrence, while keeping value judgments inspectable and contestable.

## The core loop

```text
NEED / WORLD STATE
        ↓
UNDERSTAND
        ↓
DECIDE
        ↓
COORDINATE
        ↓
ACT
        ↓
VERIFY
        ↓
OUTCOME
        ↓
LEARN
        └──────────────→ next decision gets better
```

## Why Jev?

COMMONS separates kinds of intelligence:

- **Jev / System One:** fast, typed probabilistic judgments.
- **Reasoning models:** deeper analysis, planning and explanation.
- **Policy code:** thresholds, permissions and escalation rules.
- **Tools / people / institutions:** execution.
- **Outcome records:** what actually happened.

The model does not get to rewrite its own authority.

## First working slice

The first COMMONS release will accept a real-world problem, make a small set of typed judgments with Jev, pass those judgments through an explicit policy engine, produce a route (automate / reason / escalate), and record the eventual outcome.

The first objective is deliberately small:

> **Can we reliably turn one messy human need into the right next action, know when we are uncertain, and learn whether it worked?**

## Success

Our primary metric is:

> **Problems measurably resolved per unit of intelligence cost.**

Guardrail metrics include:

- resolution rate
- time to resolution
- decision calibration
- abstention / escalation quality
- harmful-action rate
- recurrence rate
- access across languages and ability levels
- user-reported agency and benefit

See [SUCCESS.md](SUCCESS.md).

## Principles

1. **Reality is the judge.** Outputs matter only insofar as outcomes improve.
2. **Humans set goals and values.** Models do not silently define the objective.
3. **Code retains authority.** Policies and permissions live outside model weights.
4. **Uncertainty is a feature.** Systems must be able to abstain and escalate.
5. **Safe by architecture.** Dangerous actions should be difficult, observable and recoverable.
6. **Measure access, not just averages.** Intelligence that only helps the already-powerful is not enough.
7. **Start narrow, close the loop, then generalise.**
8. **Open interfaces.** COMMONS should eventually interoperate with people, models, tools, organisations and public infrastructure.
9. **No engagement objective.** Attention is not the north star.
10. **Preserve agency.** Help people become more capable, not merely more dependent.

## Roadmap in one line

```text
one need → one reliable route → one closed feedback loop
→ many domains → coordinated networks → open public intelligence infrastructure
```

Read the project documents:

- [VISION.md](VISION.md) — what we are ultimately trying to create
- [STRATEGY.md](STRATEGY.md) — working backwards from that future
- [SUCCESS.md](SUCCESS.md) — how we know whether COMMONS is actually helping
- [ARCHITECTURE.md](ARCHITECTURE.md) — the initial technical architecture

## Status

**Foundation / v0.1.**

The repository intentionally begins with a thin vertical slice rather than a sprawling agent platform.
