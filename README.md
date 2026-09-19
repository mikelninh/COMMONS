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

## Try it

```bash
git clone https://github.com/mikelninh/COMMONS.git
cd COMMONS
python -m venv .venv
# activate it, then:
pip install -e ".[dev]"
```

Set your TypeSafe key in the process environment — **never commit it**:

```powershell
$env:TYPESAFE_API_KEY="your_key_here"
```

or:

```bash
export TYPESAFE_API_KEY="your_key_here"
```

Then run:

```bash
uvicorn commons.app:app --reload
```

Open **http://127.0.0.1:8000**.

Live 32-case Jev benchmark:

```bash
python scripts/eval_civic.py
```

API-free architecture stress simulation:

```bash
python scripts/simulate_architecture.py
```


## Current working slice — v0.2 civic lab

v0.2 accepts a messy real-world problem, asks Jev a set of typed probabilistic questions, passes those judgments through inspectable policy code, and produces an accountable route. The first public demo focuses on citizens, public officials and communities.

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
- [docs/CIVIC_LAB.md](docs/CIVIC_LAB.md) — the citizen / official / community demo
- [docs/SIMULATION.md](docs/SIMULATION.md) — explicit architecture stress assumptions
- [NEXT_PHASE.md](NEXT_PHASE.md) — v0.3 evidence + capability network

## Status

**Civic intelligence lab / v0.2.**

The current slice adds multilingual civic routing, explicit deliberation boundaries, a shareable web UI, a 32-case benchmark and a measurable path toward v0.3 evidence + capabilities.
