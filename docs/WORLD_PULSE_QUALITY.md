# WORLD//PULSE — quality standard

WORLD//PULSE is the sensing layer of COMMONS: a public, shareable view of important world-state signals with enough provenance and uncertainty to be useful without pretending every number is live.

## Product promise

A person should be able to answer, in seconds:

1. **What is happening?**
2. **How fresh is this signal?**
3. **Where did it come from?**
4. **What exactly does the number mean?**
5. **What changed?**
6. **What credible action could follow?**
7. **Did that action actually help?**

v0.1 ships the first four reliably. The next milestone is the action + outcome layer.

## Non-negotiable rules

### 1. Never fake "live"

Every signal has one explicit freshness class:

- **live** — source itself updates continuously or at minute-scale.
- **near_real_time** — recent event tracking, but not an exhaustive instantaneous measurement.
- **periodic** — published daily/monthly/annual statistics.
- **modelled** — a transparent calculation or estimate from source data.

A periodic annual value must never animate like a second-by-second counter.

### 2. Every number is inspectable

Required fields:

- source
- source URL
- as-of date/time
- unit
- methodology
- freshness class
- confidence label

If an upstream source fails, show **unavailable** rather than silently reusing an unknown stale number.

### 3. Prefer authoritative primary sources

Source order:

1. official sensor / statistical / institutional source,
2. reputable research aggregator with transparent provenance,
3. secondary reporting only when the underlying source cannot be accessed.

Do not accept a source merely because it has an API.

### 4. Separate observation from interpretation

A measured or published number is not the same as:

- a causal explanation,
- a severity judgement,
- a prediction,
- an intervention recommendation.

Those layers need their own evidence.

### 5. Do not optimise for fear

The page should contain:

- things that need attention,
- things improving,
- human activity,
- context.

WORLD//PULSE is not a catastrophe engagement machine.

## Source acceptance checklist

Before a new signal enters production:

- [ ] clear metric definition
- [ ] known publisher / provenance
- [ ] known update cadence
- [ ] stable machine-readable access where possible
- [ ] timestamp or publication period available
- [ ] geographical scope explicit
- [ ] unit explicit
- [ ] known limitations documented
- [ ] duplicate / double-counting risk understood
- [ ] fallback behaviour defined
- [ ] license / reuse terms acceptable
- [ ] reason this signal helps a human understand or act

## Current live-event signal set

| Signal family | Source | Freshness | Important caveat |
|---|---|---|---|
| Earthquakes | USGS | live | rolling event feed; magnitude is not a measure of human impact |
| Natural events | NASA EONET | near-real-time | curated open-event tracker, not a complete census |
| Disaster alerts | GDACS | near-real-time | alerts support situational awareness; alert presence is not a casualty or need estimate |

The cinematic public edition intentionally focuses on **events that can change between observations**. Slow structural indicators such as energy transition, health, demography or food security belong in a separate context layer and must remain clearly labelled as periodic or modelled rather than being animated as if they were live.

## Reliability architecture

Current architecture:

- fetch independent sources in parallel,
- hard timeout per upstream request,
- tolerate partial provider failure,
- first observation is a baseline rather than a fake burst of "new" events,
- compare later observations using stable event fingerprints,
- conservative cross-source overlap detection never upgrades correlation into confirmation,
- zero paid AI by default,
- no API key required for the public event feeds.

The public static edition stores its previous observation in the visitor's browser. The backend prototype currently stores fingerprints in process memory, so a process restart resets its baseline; production change detection should use durable snapshot storage.

Next:

- persistent cache with last-known-good timestamp,
- source health monitoring,
- schema drift detection,
- automated reconciliation against alternate sources,
- historical snapshots,
- data revision tracking.

## UX quality gates

A release is not ready unless:

### Comprehension

In a five-person test, at least four people can correctly explain the difference between **live**, **periodic**, and **modelled** after using the page for under one minute.

### Trust

At least 90% of displayed values expose a working provenance path in one click. Production target is 100%.

### Performance

- meaningful content begins rendering immediately,
- source calls execute concurrently,
- cached response should feel instant,
- one slow provider must not block all providers.

### Shareability

A copied/shared pulse must preserve:

- value,
- label,
- freshness,
- as-of date,
- source.

A screenshot without provenance should not be the only share path.

### Accessibility

- keyboard usable,
- readable on narrow mobile screens,
- labels do not rely on colour alone,
- sufficient contrast,
- reduced-motion mode should be supported before wider launch.

## What would make this genuinely special

The dashboard itself is only the sensing layer.

The full COMMONS loop is:

```text
WORLD//PULSE
  ↓
signal / problem
  ↓
evidence
  ↓
possible interventions
  ↓
cost / risk / uncertainty
  ↓
who can act?
  ↓
authorised action
  ↓
outcome
  ↓
did reality improve?
  ↺
```

The key moat is not "more live statistics".

It is the transition from **traceable world state → accountable action → measured learning**.

## Next milestone: ACTION v0.1

Choose one surfaced event where useful action can be specific and measurable.

Candidate:

> A current natural disaster with a credible humanitarian response and independently verifiable responder information.

For one event, COMMONS should show:

- what happened,
- affected area,
- best available evidence,
- verified organisations responding,
- what each organisation says it currently needs,
- donation / volunteering / information actions,
- uncertainty,
- follow-up outcome signals.

No generic "help now" button. Action must be event-specific and provenance-preserving.

## North star

> **Did this increase a person's capacity to understand reality and contribute to a better outcome?**

Page views, shares and engagement are diagnostics — not the mission.
