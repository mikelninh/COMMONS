# COMMONS Red-Team Release Gate

COMMONS should try to break itself before asking the public to do it.

## Release rule

No public release merely because the demo looks good.

Before a public deployment:

1. deterministic authority and trust invariants pass;
2. capability-network simulation passes;
3. live Jev adversarial corpus is replayed;
4. authority violations must equal zero;
5. failures are inspected by class, not hidden in an aggregate score;
6. every accepted architecture change replays historical regressions.

## Current attacker classes

- ambiguity attacker
- authority escalator
- confidence trap
- political-choice attacker
- fake-evidence attacker
- capability liar
- metric gamer
- collusion attacker
- instruction injection
- cost bomb

The live corpus is in `evals/redteam_cases.json`.

Run:

```bash
python scripts/redteam_live.py
```

It requires `TYPESAFE_API_KEY`.

A failing case exits non-zero so a test run cannot be mistaken for a successful
release candidate.

## What red-team success means

It does not prove the system is safe.

It means a known class of failures has a reproducible test and current versions
do not regress on that class.

The public challenge "Try to break COMMONS" should eventually feed novel failures
back into this corpus after privacy review and de-identification.
