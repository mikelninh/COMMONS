# COMMONS Capability Network — v0.3 alpha

COMMONS treats supply as capabilities, not merely providers.

A capability can come from a person, business, nonprofit, public service, AI model,
software system, compute resource, physical resource, or future machine.

## Onboarding

1. Register a provider.
2. Declare one or more capabilities.
3. Declare location, language, capacity, unit cost, availability and requested authority.
4. Attach evidence or credentials where relevant.
5. COMMONS records the capability as `DECLARED` until verification occurs.
6. Observed outcomes update the capability's performance history.

Core invariant:

> Anyone can declare a capability. Nobody automatically earns authority.

Unverified capabilities are capped at `DRAFT`, even when the provider asks for
higher execution authority.

## Authority ladder

1. READ
2. EXPLAIN
3. TRANSLATE
4. DRAFT
5. EXECUTE_REVERSIBLE
6. EXECUTE_CONSEQUENTIAL
7. PROHIBITED

Matching must satisfy both capability fit and authority requirements.

## Matching inputs

- capability type
- semantic tags
- language
- location
- price ceiling
- required authority
- verification requirement
- observed success history

The v0.3 matcher is deliberately simple and inspectable. It is a substrate for
experiments, not yet a production marketplace ranking system.

## Example

Need: deliver surplus food tonight.

Required capabilities:

- food_surplus
- recipient_capacity
- transport

COMMONS can compose the three independently instead of assuming one organisation
must provide the entire solution.

Long-term matching question:

> What combination of available capabilities has the best chance of resolving
> this need for acceptable cost, risk, time and authority?
