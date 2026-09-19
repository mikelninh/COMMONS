# COMMONS Architecture Stress Simulation

This simulation asks a narrow question:

> If routing improves, and then COMMONS gains evidence/capabilities and bounded execution, where does the bottleneck move?

The model is intentionally simple. **These are illustrative assumptions, not measured Jev performance, not empirical estimates, and not forecasts.**

Run:

```bash
python scripts/simulate_architecture.py
```

With the fixed seed currently in the script, the 5,000-trial stress test produces approximately:

| Version | Simulated resolution | Verified resolution | Mean time | Mean intelligence cost | Brier proxy | Safety | Agency retention | Recurrence |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| v0.2 judgment only | 30.9% | 3.1% | 20.45 h | €0.011 | 0.140 | 97.2% | 93.2% | 33.7% |
| v0.3 evidence + capabilities | 58.9% | 37.3% | 7.68 h | €0.095 | 0.107 | 96.4% | 91.4% | 22.4% |
| v0.4 bounded execution | 74.1% | 64.2% | 2.71 h | €0.292 | 0.095 | 95.9% | 88.4% | 13.9% |

## Interpretation

The exact numbers are not important. The shape is.

### v0.2: routing is not resolution

A judgment layer can cheaply choose a plausible next capability, but without evidence retrieval, execution and verification most problems remain unresolved.

### v0.3: capability is the next major bottleneck

Adding authoritative evidence, reusable capabilities and outcome verification creates the largest simulated jump.

That is why v0.3 should focus on:

1. provenance-aware evidence,
2. capability registry,
3. explicit action envelopes,
4. verification,
5. outcome follow-up.

### v0.4: autonomy creates a new trade-off

Bounded execution can reduce time-to-resolution substantially, but additional authority creates pressure on safety and agency.

The design response is **not** “never execute.” It is:

- least privilege,
- explicit consent,
- reversible actions where possible,
- human review for consequential actions,
- independent verification,
- audit trails,
- recovery paths.

The simulation exists to make those trade-offs visible before we build them.
