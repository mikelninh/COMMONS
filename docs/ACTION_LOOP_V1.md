# COMMONS Action Loop v1

## Purpose

WORLD PULSE already makes a real-world event understandable. Action Loop v1 extends the product from understanding toward accountable agency:

**understand → decide → coordinate → act → follow → learn**

The first full pilot is Nepal Flash Floods 2026 because the IFRC Emergency Appeal remains active and a direct, official donation path exists.

## Truth boundary

Action Loop v1 is intentionally conservative.

- A user action can be recorded locally.
- External completion is never treated as verified unless an external system later provides evidence.
- Donation amounts, payment details and identity are not collected.
- Later official outcomes can be shown as **evidence after your action**.
- They must never be shown as **evidence caused by your action** without causal evidence.
- If no defensible direct action is known, COMMONS says so instead of inventing one.

## Action Loop schema

Each story can define:

- current problem
- goal
- actors who can act
- interventions
- evidence strength
- uncertainty
- what should be measured next
- latest official outcome
- follow-up rules

## Local action ledger

The v1 ledger is stored in localStorage under `commons.action-ledger.v1`.

Receipt states include:

- official path opened
- self-reported complete
- following
- share completed
- share prepared

A self-reported receipt is explicitly labeled as such.

## Feedback mechanism

Every receipt stores the story's evidence date at the moment of action.

When the catalog later contains a different official evidence date, WORLD PULSE can flag:

**NEWER OFFICIAL EVIDENCE**

This creates a simple inspectable return loop without claiming causality.

## Launch loops

### Nepal — Water Returns
Direct verified public action exists:
- official IFRC donation path supporting Nepal Flash Floods 2026
- follow official outcome evidence
- pass the provenance-preserving story onward

### Bhutan — The Last Transmission
No invented donation action.
- follow whether elimination holds
- inspect the WHO-validated One Health model
- share the prevention story

### DRC — Outrunning an Epidemic
No direct public intervention is surfaced in v1 because it has not been verified tightly enough.
- follow the open WHO evidence loop
- inspect the WHO outbreak hub
- share the unresolved state accurately

## What v1 does not yet do

- background monitoring
- NGO or payment-provider verification
- cross-user coordination
- intervention cost-effectiveness modeling
- causal attribution
- public action counts
- user identity
- server-side receipts

Those require new evidence, integrations, permissions or infrastructure rather than UI alone.