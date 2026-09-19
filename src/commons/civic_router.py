from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl

from commons.civic import CivicProofStage


class CivicNeedInput(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    location: str = Field(default="Berlin", max_length=300)


class CivicChannel(BaseModel):
    channel_id: str
    name: str
    channel_type: Literal[
        "participation",
        "public_funding",
        "public_space_report",
        "petition",
        "support",
    ]
    responsible_body: str
    official_source: HttpUrl
    why_it_fits: str
    what_commons_can_do: list[str]
    citizen_must_do: list[str]
    deadline: str | None = None
    caveats: list[str] = Field(default_factory=list)
    proof_stage: CivicProofStage = CivicProofStage.SOURCE_VERIFIED
    last_verified: date


class CivicTraceStep(BaseModel):
    step: int
    label: str
    status: Literal["done", "warning"]
    detail: str


class CivicActionResult(BaseModel):
    need: str
    location: str
    interpreted_as: str
    channels: list[CivicChannel]
    primary_channel_id: str
    checked_channels: int
    matched_signals: list[str] = Field(default_factory=list)
    routing_trace: list[CivicTraceStep] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    political_recommendation: bool = False
    citizen_voice_required: bool = True


VERIFIED = date(2026, 9, 19)


MEINBERLIN = CivicChannel(
    channel_id="berlin-meinberlin",
    name="meinBerlin",
    channel_type="participation",
    responsible_body="Land Berlin / participating Senate and district administrations",
    official_source="https://mein.berlin.de/",
    why_it_fits=(
        "Berlin's central participation platform publishes current public participation "
        "projects and lets residents submit ideas, comments, votes or survey responses "
        "where a project supports them."
    ),
    what_commons_can_do=[
        "Find relevant current participation projects",
        "Summarise the official project and participation window",
        "Structure the citizen's own idea or comment",
        "Prepare a draft for citizen review",
    ],
    citizen_must_do=[
        "Choose their own position or idea",
        "Review the wording",
        "Submit or approve any contribution themselves",
    ],
    last_verified=VERIFIED,
)

HELLE_MITTE_FUND = CivicChannel(
    channel_id="berlin-helle-mitte-fund-2026",
    name="Gebietsfonds Helle Mitte",
    channel_type="public_funding",
    responsible_body="Bezirksamt Marzahn-Hellersdorf / Standortmanagement Helle Mitte",
    official_source=(
        "https://www.berlin.de/ba-marzahn-hellersdorf/aktuelles/"
        "pressemitteilungen/2026/pressemitteilung.1713001.php"
    ),
    why_it_fits=(
        "A current local fund supports eligible projects in Helle Mitte. "
        "Private individuals, businesses, associations and institutions can apply."
    ),
    what_commons_can_do=[
        "Check whether the proposed project appears to fit the published area and examples",
        "Turn the citizen's idea into an application checklist",
        "Identify missing budget and implementation details",
        "Draft application text from the citizen's own stated goals",
    ],
    citizen_must_do=[
        "Confirm the project and factual claims",
        "Provide the real budget and implementation plan",
        "Submit the application through the official channel",
    ],
    deadline="2026-10-25",
    caveats=[
        "The fund covers up to 50% of eligible project costs.",
        "A local jury decides on funding; COMMONS cannot predict or promise an award.",
    ],
    last_verified=VERIFIED,
)

ORDNUNGSAMT = CivicChannel(
    channel_id="berlin-ordnungsamt-online",
    name="Ordnungsamt-Online",
    channel_type="public_space_report",
    responsible_body="Berlin district offices / Ordnungsämter",
    official_source="https://www.berlin.de/ordnungsamt-online/hinweise/",
    why_it_fits=(
        "The official portal accepts reports and complaints about problems and disturbances "
        "in public space, including examples such as rubbish and road damage."
    ),
    what_commons_can_do=[
        "Help describe the issue factually",
        "Organise location, time and evidence",
        "Prepare a concise report for citizen review",
        "Track the external receipt or case reference if the citizen supplies it",
    ],
    citizen_must_do=[
        "Confirm the report is accurate",
        "Submit or approve the submission",
        "Provide any case/reference number received",
    ],
    caveats=[
        "The portal is not for matters requiring immediate intervention.",
        "Emergencies must go directly to the appropriate emergency service.",
    ],
    last_verified=VERIFIED,
)

PETITION = CivicChannel(
    channel_id="berlin-petitionsausschuss",
    name="Petitionsausschuss des Abgeordnetenhauses von Berlin",
    channel_type="petition",
    responsible_body="Abgeordnetenhaus von Berlin",
    official_source=(
        "https://www.parlament-berlin.de/das-parlament/petitionen/"
        "online-petition/petitionsverfahren-und-datenschutz"
    ),
    why_it_fits=(
        "The committee handles petitions concerning Berlin administration and suggestions "
        "for Berlin legislation, and can investigate complaints about Berlin authorities."
    ),
    what_commons_can_do=[
        "Explain the official petition process",
        "Help organise facts and supporting documents",
        "Draft a neutral petition from the citizen's own account",
        "Track confirmation and the committee's written response",
    ],
    citizen_must_do=[
        "Decide the complaint or request they want to make",
        "Review all factual claims",
        "Confirm the online petition by the emailed confirmation link",
    ],
    caveats=[
        "This is not a substitute for a court challenge or other time-limited legal remedy.",
        "The committee cannot overturn or review court decisions.",
        "Private disputes and federal/other-state administration may fall outside its remit.",
    ],
    last_verified=VERIFIED,
)


def route_civic_need(need: CivicNeedInput) -> CivicActionResult:
    text = need.text.lower()
    channels: list[CivicChannel] = []
    missing: list[str] = []
    signals: list[str] = []

    project_words = (
        "project", "projekt", "idea", "idee", "neighborhood", "neighbourhood",
        "kiez", "quartier", "community", "nachbarschaft", "fund", "förder",
        "beteilig", "mitmachen", "improve", "verbessern",
    )
    public_space_words = (
        "müll", "trash", "rubbish", "garbage", "road", "straße", "strasse",
        "pothole", "schlagloch", "broken", "kaputt", "public space",
        "öffentlichen raum", "unsafe crossing", "gefährlich",
    )
    authority_words = (
        "behörde", "authority", "amt", "bescheid", "decision", "entscheidung",
        "complaint", "beschwer", "unverständlich", "unfair", "wrong",
        "falsch", "waiting", "wart",
    )

    if "helle mitte" in text or "hellersdorf" in text:
        channels.append(HELLE_MITTE_FUND)
        signals.append("Helle Mitte / Hellersdorf location or project context")

    if any(word in text for word in project_words):
        channels.append(MEINBERLIN)
        signals.append("local project / participation language")

    if any(word in text for word in public_space_words):
        channels.append(ORDNUNGSAMT)
        signals.append("public-space problem language")

    if any(word in text for word in authority_words):
        channels.append(PETITION)
        signals.append("Berlin authority / complaint language")
        if "bescheid" in text or "decision" in text or "entscheidung" in text:
            missing.append(
                "If this is a formal administrative decision, check the notice for any "
                "Rechtsbehelfsbelehrung and deadline before relying on a petition route."
            )

    if not channels:
        channels.append(MEINBERLIN)
        signals.append("no specific verified route matched")
        missing.append(
            "COMMONS does not yet have enough verified Berlin channels to route this "
            "confidently. The first safe step is to search current official participation "
            "projects rather than invent a responsible authority."
        )

    # Deduplicate while preserving priority.
    unique = {channel.channel_id: channel for channel in channels}

    if HELLE_MITTE_FUND.channel_id in unique:
        interpreted = "local project / public funding opportunity"
    elif ORDNUNGSAMT.channel_id in unique:
        interpreted = "public-space issue / service report"
    elif PETITION.channel_id in unique:
        interpreted = "complaint or request concerning Berlin administration"
    else:
        interpreted = "civic participation / local improvement"

    routed_channels = list(unique.values())
    primary = routed_channels[0]
    trace = [
        CivicTraceStep(
            step=1,
            label="Read your goal",
            status="done",
            detail=f"Captured your request as written and scoped it to {need.location}.",
        ),
        CivicTraceStep(
            step=2,
            label="Understand the civic need",
            status="warning" if signals == ["no specific verified route matched"] else "done",
            detail=f"Matched: {', '.join(signals)}.",
        ),
        CivicTraceStep(
            step=3,
            label="Check verified official channels",
            status="done",
            detail=(
                "Checked the current curated Berlin civic channel set and returned only "
                "routes backed by official public sources."
            ),
        ),
        CivicTraceStep(
            step=4,
            label="Apply authority and safety boundaries",
            status="warning" if missing else "done",
            detail=(
                "COMMONS keeps the citizen's position and final submission under citizen "
                "control; legal-remedy or emergency caveats are surfaced rather than hidden."
            ),
        ),
        CivicTraceStep(
            step=5,
            label="Choose the clearest next path",
            status="done",
            detail=f"Primary route: {primary.name}. {len(routed_channels)} route(s) remain visible.",
        ),
    ]

    return CivicActionResult(
        need=need.text,
        location=need.location,
        interpreted_as=interpreted,
        channels=routed_channels,
        primary_channel_id=primary.channel_id,
        checked_channels=4,
        matched_signals=signals,
        routing_trace=trace,
        missing_information=missing,
    )
