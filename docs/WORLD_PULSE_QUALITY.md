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

## v0.1 signal set

| Signal | Source | Freshness | Important caveat |
|---|---|---|---|
| Open natural events | NASA EONET | near-real-time | curated event tracker, not a complete census |
| Open wildfire events | NASA EONET | near-real-time | events, not satellite hotspot detections |
| M4.5+ earthquakes / 24h | USGS | live | count changes as the rolling 24h window moves |
| Estimated births / day | World Bank + UN inputs | modelled | annual-rate estimate, not a live birth feed |
| Renewable electricity share | OWID / Ember + sources | periodic | annual structural indicator |
| Global life expectancy | OWID + source datasets | periodic | annual structural indicator |

## Reliability architecture

v0.1:

- fetch independent sources in parallel,
- hard timeout per upstream request,
- five-minute in-memory cache,
- partial response when one provider fails,
- explicit warning listing unavailable providers,
- no API key required for the core six signals.

Later:

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

Choose one signal where useful action can be specific and measurable.

Candidate:

> A current natural disaster with a credible humanitarian response.

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
