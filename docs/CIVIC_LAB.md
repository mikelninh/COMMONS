# COMMONS Civic Intelligence Lab — v0.2

The civic lab is the first public demonstration of COMMONS as a decision-and-coordination substrate.

It has three modes:

## Citizen

Use COMMONS to understand a public-service or civic situation, identify missing information, find the right capability, and make the next step clearer.

Examples:

- understand an administrative letter,
- identify the correct public service,
- understand a consultation process,
- surface evidence gaps,
- translate before taking action.

## Public official

Use COMMONS to make a decision process more inspectable before a consequential choice is made.

It can surface:

- affected groups,
- evidence still needed,
- implementation constraints,
- urgency,
- reversibility,
- automation risk,
- need for accountable human review,
- legitimate value conflicts.

COMMONS does **not** select the preferred political outcome. For contested civic choices the policy engine routes to `deliberate`: structure the decision, preserve uncertainty, and keep the choice with people and legitimate institutions.

## Community

Use COMMONS to coordinate people and organisations around a shared problem.

Examples:

- identify duplicated effort and missing capabilities,
- decide what information must be collected,
- route work to people or tools,
- structure a fair process when groups have conflicting needs.

---

## What Jev does

Jev receives messy state and answers focused typed questions:

- domain,
- urgency,
- high stakes,
- information sufficiency,
- automation safety,
- need for human review,
- affected groups,
- contested values,
- evidence need,
- reversibility,
- required capability.

The policy layer then decides which routes are permitted.

**Confidence is not authority.**

A model can be highly confident and still be prevented from executing a consequential action.

---

## What v0.2 proves

The demo can test whether the decision substrate is useful:

- does it classify messy civic needs?
- does it abstain when context is missing?
- does it recognise consequential cases?
- does it preserve human authority over contested choices?
- does it work across languages?
- are its probabilities useful enough for explicit policy thresholds?

It does **not** yet prove that COMMONS resolves real civic problems. That requires evidence retrieval, real capabilities, execution, verification and follow-up.

---

## Metrics

| Metric | v0.2 can measure? | How |
| --- | --- | --- |
| Resolution rate | Not yet | real outcome follow-up |
| Time to resolution | Not yet | real outcome follow-up |
| Intelligence cost | Partly | model input tokens and API pricing |
| Calibration | Proxy | labelled-case Brier scores |
| Safety | Yes, partially | false-safe and authority-violation rates |
| Access | Yes, partially | performance by language/mode |
| Recurrence | Not yet | longitudinal follow-up |
| Agency | Not yet | user-reported + behavioural measures |

Run the benchmark with:

```bash
python scripts/eval_civic.py
```

The benchmark uses 32 synthetic cases in English, German and Vietnamese. Synthetic labels are test hypotheses, not ground truth about what a political or administrative outcome ought to be.
