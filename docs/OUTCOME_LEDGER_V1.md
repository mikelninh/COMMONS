# Outcome Ledger v1

COMMONS is the **learning/outcome layer**, not a second execution runtime.

It can ingest portable `openaction.agency-receipt.v1` records emitted by systems such as OpsPilot, Game Studio, HANA, CivicOS or Cyber Resilience and normalize them into `commons.outcome-record.v1`.

The ledger preserves:

- what mission produced the record;
- who owned the decision;
- what authority the action had;
- whether external side effects occurred;
- what outcome evidence exists;
- whether that evidence is synthetic, observed or failure evidence;
- what changes next or remains unknown.

It deliberately does **not** produce one universal impact score. Saving time, reducing suffering, making art meaningful, recovering a benefit and creating a joyful game are different human outcomes. COMMONS can compare evidence quality and recurrence while leaving value judgments visible rather than hiding them inside one scalar.

A synthetic receipt stays synthetic after ingestion. COMMONS does not upgrade evidence merely because another system consumed it.
