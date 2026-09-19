# COMMONS Architecture

## Core rule

> **Models propose or judge. Policy code decides authority. Actions are explicit. Outcomes close the loop.**

---

# v0.1 pipeline

```text
                         ┌─────────────────────┐
                         │    Problem Intake    │
                         │ free-form human need │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │   Decision Layer     │
                         │       Jev            │
                         │ Choice/Noul/Score    │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │    Policy Engine     │
                         │ deterministic code  │
                         └──────────┬──────────┘
                                    │
                   ┌────────────────┼────────────────┐
                   ▼                ▼                ▼
                REASON           REQUEST          ESCALATE
                                  INFO
                   │                                 │
                   └────────────────┬────────────────┘
                                    ▼
                         ┌─────────────────────┐
                         │    Action Record     │
                         │ proposed/executed    │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │    Outcome Record    │
                         │ verified result      │
                         └──────────┬──────────┘
                                    │
                                    ▼
                               EVALUATION
```

---

# Components

## Intake

Input:

- natural-language problem,
- optional structured context,
- language,
- source,
- user constraints.

The intake layer should preserve original input. Normalisation must not silently erase relevant details.

## Decision layer

Jev receives the same state and answers multiple focused questions.

Initial questions:

### domain — Choice

Candidate set:

- education
- health
- legal
- public_services
- finance
- business
- software
- science
- agriculture
- logistics
- personal
- other

### urgency — Score

0. no time pressure  
1. routine  
2. time-sensitive  
3. urgent  
4. immediate

### high_stakes — Noul

Probability that a wrong action could materially affect health, safety, legal status, finances, rights or another high-impact domain.

### enough_information — Noul

Probability that enough information exists to choose a useful next route.

### safe_to_automate — Noul

Probability that the next action can be automated under current permissions and foreseeable risk.

### needs_human_review — Noul

Probability that human review should occur before consequential action.

### capability — Choice

- retrieve
- calculate
- reason
- translate
- specialist
- workflow
- human
- other

The exact taxonomy is expected to evolve from evaluation evidence.

---

# Policy engine

The policy engine consumes model outputs but is ordinary deterministic code.

Illustrative rules:

```text
if high_stakes >= 0.70:
    ESCALATE

elif needs_human_review >= 0.70:
    ESCALATE

elif enough_information <= 0.45:
    REQUEST_INFO

elif decision confidence is low:
    REQUEST_INFO or ESCALATE

else:
    route to selected capability
```

Thresholds are versioned.

Changing a policy should create a new policy version.

---

# Decision record

Every run should eventually persist:

```json
{
  "case_id": "...",
  "created_at": "...",
  "input": {...},
  "decision_model": "...",
  "decision_model_version": "...",
  "questions": {...},
  "answers": {...},
  "policy_version": "...",
  "route": "...",
  "reason": "...",
  "action": null,
  "outcome": null
}
```

This is the minimum substrate for auditability, replay and learning.

---

# Outcome record

An outcome is separate from a model response.

Possible fields:

```json
{
  "case_id": "...",
  "status": "resolved | partial | unresolved | harmful | unknown",
  "verified": true,
  "verification_method": "user | system | expert | external evidence",
  "time_to_resolution_seconds": 120,
  "user_benefit": 4,
  "recurrence": false,
  "notes": "..."
}
```

Not every domain will use every field.

---

# Capability interface

Future capabilities should expose at least:

```text
id
description
accepted_input
possible_actions
required_permissions
risk_class
cost_model
execution_method
verification_method
```

This lets COMMONS route to capabilities without hard-wiring every provider.

---

# Safety architecture

## Least authority

A capability receives only the permissions necessary for its action.

## Explicit consequence boundary

Reading, advising, drafting and executing are different permission levels.

## Human escalation

High-stakes or low-confidence paths can require review.

## Immutable audit

Decision, policy and action records should be append-oriented.

## Recovery

Capabilities should declare whether an action is reversible and how to compensate for failure.

## Independent evaluation

The system performing an action should not be the only component judging whether the action was safe or successful.

---

# Technology choices for v0.1

- Python 3.12+
- `typesafe-sdk` for Jev
- Pydantic for schemas
- FastAPI for a minimal HTTP interface
- SQLite initially for decision/outcome records
- pytest for deterministic policy tests

We optimise for legibility and iteration speed.

Infrastructure complexity comes later.
