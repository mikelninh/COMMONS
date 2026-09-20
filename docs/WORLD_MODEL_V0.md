# COMMONS World Model v0

## Purpose

WORLD PULSE explains what changed.

World Model v0 begins to preserve a deeper loop:

**state → forecast → memory → response → outcome → learning**

The first fully instrumented pilot is:

## Loop 01 — When the Water Rises

The pilot combines three independent forecast providers, a long historical weather record, and river-discharge guidance.

### Forecast Council

The current council uses:

- ECMWF IFS
- NOAA GFS
- DWD ICON

The first score is deliberately simple: the system compares deterministic 72-hour precipitation, temperature and wind-gust forecasts.

`high / medium / low agreement` means only that model spread is small / moderate / large.

It is **not** a calibrated probability.

Future versions should use ensemble distributions and proper probabilistic scoring.

### Weather Memory

ERA5 reanalysis is used to compare the forecast 72-hour precipitation total with historical three-day precipitation totals near the same time of year.

The system reports:

- seasonal percentile
- closest historical precipitation-total analogues
- historical period used

This is verified physical history.

It is not yet a full atmospheric analogue search.

Most importantly:

**similar weather does not imply similar human impact.**

Population, infrastructure, land use, warnings, preparedness and response capacity may differ substantially.

### Flood signal

GloFAS v4 simulated river discharge provides:

- forecast peak discharge
- historical discharge percentile
- historical baseline

This is large-scale flood guidance.

It is not a local flood warning, and the selected model river may not exactly match the local river of interest.

## The first ten loops

1. When the Water Rises — flood
2. Before the Storm Arrives — tropical cyclone
3. The Heat We Cannot See — extreme heat
4. When the Forest Burns — wildfire and smoke
5. The Air We Breathe — air quality
6. When Rain Doesn't Come — drought
7. Can We Stop an Outbreak? — disease
8. When the Ground Moves — earthquake
9. Will There Be Enough to Eat? — food insecurity
10. When Humanity Succeeds — recovery, elimination and restoration

Only Loop 01 is labelled `live_pilot`.

Other loops explicitly expose their current coverage state.

## Snapshot archive

`.github/workflows/world-model.yml` creates a snapshot every six hours.

Each snapshot is:

1. deployed as the current public research state
2. uploaded as a GitHub Actions artifact
3. archived on the `world-model-data` branch

This lets future evaluation reconstruct:

- what COMMONS knew
- what each model predicted
- when the prediction was made
- what actually happened later

That is the foundation for honest backtesting.

## Cost discipline

The World Model should store selected watchpoints, derived state, forecasts, claims, historical analogues and evaluation results.

It should not mirror entire global weather archives.

Source providers already host the large datasets.

The cost advantage comes from storing the questions and the evidence needed to answer them, not petabytes of atmosphere.

## Provider / licence boundary

The research prototype can use Open-Meteo's free hosted API only while the use remains non-commercial.

Before commercial use, COMMONS must either:

- connect an appropriate commercial Open-Meteo plan and customer endpoint, or
- ingest the underlying open data directly under its applicable licence and attribution requirements.

`OpenMeteoClient(commercial=True)` fails closed without an API key and explicitly configured customer endpoints.

This is intentional.

## What comes next

### v0.2

- ensemble forecasts
- forecast probabilities
- calibration curves
- Brier score / CRPS
- cyclone track source
- air-quality source
- wildfire detections
- drought indices

### v0.3

- exposure
- assets / population
- verified response actors
- historical human outcomes
- impact model

### v1

- continuous ten-loop operation
- independent evaluation
- source redundancy
- professional watchlists
- reliable API
