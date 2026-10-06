from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any

from rdflib import Graph, Literal, Namespace, RDF, RDFS, URIRef, XSD

CITY = Namespace("https://commons.local/semantic-city/")
PROV = Namespace("http://www.w3.org/ns/prov#")


class Authority(StrEnum):
    INFORM = "inform"
    RECOMMEND = "recommend"
    HUMAN_DECISION_REQUIRED = "human_decision_required"
    NEVER_AUTO_EXECUTE = "never_auto_execute"


@dataclass(frozen=True)
class ScenarioSpec:
    id: str
    title: str
    question: str
    intent: str
    authority: Authority
    query: str
    recommendation: str
    caveat: str


@dataclass(frozen=True)
class ScenarioResult:
    id: str
    title: str
    question: str
    authority: str
    recommendation: str
    caveat: str
    query: str
    rows: list[dict[str, Any]]
    evidence: list[dict[str, str]]
    graph_stats: dict[str, int]
    validation: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


SHACL_TTL = """
@prefix city: <https://commons.local/semantic-city/> .
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

city:ObservationShape a sh:NodeShape ;
    sh:targetClass city:Observation ;
    sh:property [ sh:path city:metric ; sh:minCount 1 ; sh:maxCount 1 ] ;
    sh:property [ sh:path city:value ; sh:minCount 1 ; sh:maxCount 1 ] ;
    sh:property [ sh:path city:evidenceSource ; sh:minCount 1 ] ;
    sh:property [ sh:path city:evidenceClass ; sh:minCount 1 ; sh:maxCount 1 ] ;
    sh:property [ sh:path city:isDemoValue ; sh:minCount 1 ; sh:maxCount 1 ; sh:datatype xsd:boolean ] .

city:RecommendationShape a sh:NodeShape ;
    sh:targetClass city:Recommendation ;
    sh:property [ sh:path city:authority ; sh:minCount 1 ; sh:maxCount 1 ] ;
    sh:property [ sh:path city:because ; sh:minCount 1 ] ;
    sh:property [ sh:path city:requiresHumanApproval ; sh:minCount 1 ; sh:maxCount 1 ; sh:datatype xsd:boolean ] .
"""


SOURCE_REGISTRY = {
    "heat": {
        "label": "Heat / climate analysis",
        "publisher": "Umweltatlas Berlin",
        "endpoint": "https://gdi.berlin.de/services/wfs/ua_klimaanalyse_2022",
        "evidence_class": "structural",
        "caveat": "Planning/climate analysis, not today's measured temperature.",
    },
    "justice": {
        "label": "Environmental-justice context",
        "publisher": "Umweltatlas Berlin",
        "endpoint": "https://gdi.berlin.de/services/wfs/ua_umweltgerechtigkeit2023",
        "evidence_class": "structural",
        "caveat": "Official burden context; the demo does not invent a morality score.",
    },
    "green": {
        "label": "Public green spaces",
        "publisher": "Geoportal Berlin",
        "endpoint": "https://gdi.berlin.de/services/wfs/gruenanlagen",
        "evidence_class": "structural",
        "caveat": "Mapped green space is not the same as shade or cooling quality.",
    },
    "hospitals": {
        "label": "Hospitals",
        "publisher": "Geoportal Berlin",
        "endpoint": "https://gdi.berlin.de/services/wfs/krankenhaeuser",
        "evidence_class": "structural",
        "caveat": "Proximity is not capacity or guaranteed access.",
    },
    "weather": {
        "label": "Weather model",
        "publisher": "Open-Meteo",
        "endpoint": "https://api.open-meteo.com/",
        "evidence_class": "modeled",
        "caveat": "Model output, not an on-site sensor reading.",
    },
    "transit": {
        "label": "Transit movement",
        "publisher": "VBB",
        "endpoint": "https://vbb.transport.rest/",
        "evidence_class": "live",
        "caveat": "Movement availability does not guarantee accessibility or capacity.",
    },
}


def _u(local: str) -> URIRef:
    return CITY[local]


def _add_label(g: Graph, node: URIRef, label: str, cls: URIRef) -> None:
    g.add((node, RDF.type, cls))
    g.add((node, RDFS.label, Literal(label)))


def _source(g: Graph, key: str) -> URIRef:
    source = SOURCE_REGISTRY[key]
    node = _u(f"source/{key}")
    _add_label(g, node, source["label"], CITY.EvidenceSource)
    g.add((node, CITY.publisher, Literal(source["publisher"])))
    g.add((node, CITY.endpoint, Literal(source["endpoint"], datatype=XSD.anyURI)))
    g.add((node, CITY.evidenceClass, Literal(source["evidence_class"])))
    g.add((node, CITY.caveat, Literal(source["caveat"])))
    return node


def _observation(
    g: Graph,
    obs_id: str,
    subject: URIRef,
    metric: str,
    value: float,
    source: URIRef,
    evidence_class: str,
    unit: str | None = None,
) -> URIRef:
    node = _u(f"observation/{obs_id}")
    _add_label(g, node, f"{metric}: {value}", CITY.Observation)
    g.add((node, CITY.about, subject))
    g.add((node, CITY.metric, Literal(metric)))
    g.add((node, CITY.value, Literal(value, datatype=XSD.decimal)))
    g.add((node, CITY.evidenceSource, source))
    g.add((node, CITY.evidenceClass, Literal(evidence_class)))
    g.add((node, CITY.isDemoValue, Literal(True, datatype=XSD.boolean)))
    if unit:
        g.add((node, CITY.unit, Literal(unit)))
    g.add((subject, CITY.hasObservation, node))
    return node


def build_demo_graph() -> Graph:
    """Build a deterministic Berlin semantic-city fixture.

    Entity relationships and source mappings are representative. Numeric values are
    deliberately marked city:isDemoValue true so nobody can mistake this fixture
    for current operational city data.
    """
    g = Graph()
    g.bind("city", CITY)
    g.bind("prov", PROV)

    berlin = _u("city/berlin")
    _add_label(g, berlin, "Berlin", CITY.City)

    heat_src = _source(g, "heat")
    justice_src = _source(g, "justice")
    green_src = _source(g, "green")
    hospital_src = _source(g, "hospitals")
    weather_src = _source(g, "weather")
    transit_src = _source(g, "transit")

    cell_a = _u("area/demo-cell-a")
    _add_label(g, cell_a, "Demo Cell A - Berlin", CITY.Area)
    g.add((cell_a, CITY.locatedIn, berlin))
    vulnerable = _u("population/heat-vulnerable-a")
    _add_label(g, vulnerable, "Heat-sensitive residents - demo cohort", CITY.PopulationGroup)
    g.add((vulnerable, CITY.livesIn, cell_a))
    g.add((cell_a, CITY.containsPopulation, vulnerable))
    _observation(g, "heat-risk-a", cell_a, "heatRisk", 0.86, heat_src, "structural")
    _observation(g, "social-burden-a", cell_a, "socialBurden", 0.72, justice_src, "structural")
    _observation(g, "green-access-a", cell_a, "greenAccess", 0.31, green_src, "structural")
    _observation(g, "forecast-temp-a", cell_a, "forecastMaxTemp", 34.0, weather_src, "modeled", "degC")

    cooling = _u("action/open-cooling-space")
    _add_label(g, cooling, "Evaluate opening a cooling space", CITY.Action)
    g.add((cooling, CITY.targets, cell_a))
    g.add((cooling, CITY.requiresHumanApproval, Literal(True, datatype=XSD.boolean)))

    substation = _u("asset/substation-demo-17")
    intersection = _u("asset/intersection-demo-42")
    signal = _u("asset/traffic-signal-demo-42")
    route = _u("service/bus-route-demo")
    hospital = _u("service/hospital-access-demo")
    for node, label, cls in (
        (substation, "Substation 17 - synthetic", CITY.InfrastructureAsset),
        (intersection, "Intersection 42 - synthetic", CITY.InfrastructureAsset),
        (signal, "Traffic signal 42 - synthetic", CITY.InfrastructureAsset),
        (route, "Bus route link - synthetic", CITY.MobilityService),
        (hospital, "Hospital access route - synthetic", CITY.CareService),
    ):
        _add_label(g, node, label, cls)
        g.add((node, CITY.locatedIn, berlin))
    g.add((intersection, CITY.dependsOn, substation))
    g.add((signal, CITY.dependsOn, substation))
    g.add((route, CITY.dependsOn, signal))
    g.add((hospital, CITY.dependsOn, route))
    g.add((hospital, CITY.evidenceSource, hospital_src))
    g.add((route, CITY.evidenceSource, transit_src))

    for key, label, co2, cost, social in (
        ("a", "Building A - synthetic", 82.0, 1.8, 0.70),
        ("b", "Building B - synthetic", 56.0, 1.0, 0.42),
        ("c", "Building C - synthetic", 91.0, 2.4, 0.81),
    ):
        building = _u(f"asset/building-{key}")
        _add_label(g, building, label, CITY.Building)
        g.add((building, CITY.locatedIn, berlin))
        _observation(g, f"co2-{key}", building, "avoidableCO2", co2, heat_src, "demo-derived", "tCO2e/y")
        _observation(g, f"cost-{key}", building, "renovationCost", cost, heat_src, "demo-derived", "EURm")
        _observation(g, f"social-{key}", building, "socialPriority", social, justice_src, "demo-derived")

    road = _u("asset/flood-road-demo")
    care = _u("service/care-facility-demo")
    flood_route = _u("service/emergency-route-demo")
    for node, label, cls in (
        (road, "Flood-prone road segment - synthetic", CITY.InfrastructureAsset),
        (care, "Care facility - synthetic", CITY.CareService),
        (flood_route, "Emergency access route - synthetic", CITY.MobilityService),
    ):
        _add_label(g, node, label, cls)
        g.add((node, CITY.locatedIn, berlin))
    g.add((care, CITY.dependsOn, flood_route))
    g.add((flood_route, CITY.dependsOn, road))
    _observation(g, "flood-exposure-road", road, "floodExposure", 0.79, weather_src, "modeled")
    _observation(g, "care-criticality", care, "serviceCriticality", 0.93, hospital_src, "structural")

    human = _u("authority/municipal-human")
    _add_label(g, human, "Accountable municipal decision-maker", CITY.HumanAuthority)
    for action_id, label in (
        ("heat", "Heat resilience recommendation"),
        ("resilience", "Infrastructure cascade recommendation"),
        ("energy", "Renovation prioritisation recommendation"),
        ("flood", "Flood attention recommendation"),
    ):
        rec = _u(f"recommendation/{action_id}")
        _add_label(g, rec, label, CITY.Recommendation)
        g.add((rec, CITY.authority, Literal(Authority.HUMAN_DECISION_REQUIRED.value)))
        g.add((rec, CITY.requiresHumanApproval, Literal(True, datatype=XSD.boolean)))
        g.add((rec, CITY.controlledBy, human))
        g.add((rec, CITY.because, Literal(
            "Evidence may support prioritisation, but the consequential allocation "
            "or operational decision remains human."
        )))

    return g


SCENARIOS: dict[str, ScenarioSpec] = {
    "heat": ScenarioSpec(
        id="heat",
        title="Heat resilience",
        question="Who should receive attention first during a severe heat event, and why?",
        intent="Connect heat, social burden, green access and forecast evidence without inventing a single opaque risk score.",
        authority=Authority.HUMAN_DECISION_REQUIRED,
        query="""
            PREFIX city: <https://commons.local/semantic-city/>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            SELECT ?area ?label ?heat ?burden ?green ?temp WHERE {
              ?area a city:Area ; rdfs:label ?label .
              ?o1 city:about ?area ; city:metric "heatRisk" ; city:value ?heat .
              ?o2 city:about ?area ; city:metric "socialBurden" ; city:value ?burden .
              ?o3 city:about ?area ; city:metric "greenAccess" ; city:value ?green .
              ?o4 city:about ?area ; city:metric "forecastMaxTemp" ; city:value ?temp .
              FILTER(?heat >= 0.70)
            }
            ORDER BY DESC(?heat)
        """,
        recommendation="Prioritise human review of Demo Cell A for heat-response planning; inspect the contributing evidence before allocating resources.",
        caveat="All numeric values in this fixture are illustrative. Production use must query current official data and preserve its metadata/freshness.",
    ),
    "resilience": ScenarioSpec(
        id="resilience",
        title="Critical infrastructure cascade",
        question="What could be affected if a critical infrastructure asset fails?",
        intent="Traverse dependencies rather than treating infrastructure layers as isolated map objects.",
        authority=Authority.NEVER_AUTO_EXECUTE,
        query="""
            PREFIX city: <https://commons.local/semantic-city/>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            SELECT ?dependent ?label WHERE {
              ?dependent city:dependsOn+ <https://commons.local/semantic-city/asset/substation-demo-17> ; rdfs:label ?label .
            }
            ORDER BY ?label
        """,
        recommendation="Surface the dependency chain for an operator; do not autonomously reroute traffic, transit, energy or emergency services.",
        caveat="The dependency topology is synthetic and exists only to demonstrate semantic traversal and authority boundaries.",
    ),
    "energy": ScenarioSpec(
        id="energy",
        title="Energy transition prioritisation",
        question="Which renovation candidates deserve deeper assessment under a constrained budget?",
        intent="Compare climate benefit, cost and social context while keeping the value trade-off explicit.",
        authority=Authority.HUMAN_DECISION_REQUIRED,
        query="""
            PREFIX city: <https://commons.local/semantic-city/>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            SELECT ?building ?label ?co2 ?cost ?social ((?co2 / ?cost) AS ?co2PerMillion) WHERE {
              ?building a city:Building ; rdfs:label ?label .
              ?o1 city:about ?building ; city:metric "avoidableCO2" ; city:value ?co2 .
              ?o2 city:about ?building ; city:metric "renovationCost" ; city:value ?cost .
              ?o3 city:about ?building ; city:metric "socialPriority" ; city:value ?social .
            }
            ORDER BY DESC(?co2PerMillion)
        """,
        recommendation="Use the ranked evidence as a shortlist, then let accountable people choose the trade-off between carbon, cost, feasibility and social priority.",
        caveat="No funding decision should be automated from a composite score; weights are policy choices and must remain inspectable.",
    ),
    "flood": ScenarioSpec(
        id="flood",
        title="Heavy-rain / flood attention routing",
        question="What needs attention first before a forecast heavy-rain event?",
        intent="Connect forecast exposure to services that depend on exposed infrastructure.",
        authority=Authority.NEVER_AUTO_EXECUTE,
        query="""
            PREFIX city: <https://commons.local/semantic-city/>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            SELECT ?service ?label ?criticality WHERE {
              ?road a city:InfrastructureAsset .
              ?flood city:about ?road ; city:metric "floodExposure" ; city:value ?exposure .
              ?route city:dependsOn ?road .
              ?service city:dependsOn ?route ; rdfs:label ?label .
              ?critical city:about ?service ; city:metric "serviceCriticality" ; city:value ?criticality .
              FILTER(?exposure >= 0.70)
            }
            ORDER BY DESC(?criticality)
        """,
        recommendation="Escalate the exposed dependency chain to an operator for verification and contingency planning; keep alerts distinct from operational commands.",
        caveat="Forecasts and exposure models can be wrong. Operational action requires current verification and accountable authority.",
    ),
}


def _term_to_json(value: Any) -> Any:
    if isinstance(value, Literal):
        return value.toPython()
    if isinstance(value, URIRef):
        text = str(value)
        return text.replace(str(CITY), "city:") if text.startswith(str(CITY)) else text
    return str(value)


def validate_graph(graph: Graph) -> dict[str, Any]:
    """Use SHACL when available, with a critical-invariant fallback."""
    try:
        from pyshacl import validate  # type: ignore

        shapes = Graph().parse(data=SHACL_TTL, format="turtle")
        conforms, _results_graph, results_text = validate(
            data_graph=graph,
            shacl_graph=shapes,
            inference="rdfs",
            abort_on_first=False,
            allow_infos=True,
            allow_warnings=True,
        )
        return {
            "engine": "pyshacl",
            "conforms": bool(conforms),
            "summary": (
                results_text.strip().splitlines()[0]
                if results_text
                else "SHACL validation completed"
            ),
        }
    except ImportError:
        problems: list[str] = []
        for obs in graph.subjects(RDF.type, CITY.Observation):
            for required in (
                CITY.metric,
                CITY.value,
                CITY.evidenceSource,
                CITY.evidenceClass,
                CITY.isDemoValue,
            ):
                if graph.value(obs, required) is None:
                    problems.append(f"{obs} missing {required}")
        for rec in graph.subjects(RDF.type, CITY.Recommendation):
            for required in (
                CITY.authority,
                CITY.because,
                CITY.requiresHumanApproval,
            ):
                if graph.value(rec, required) is None:
                    problems.append(f"{rec} missing {required}")
        return {
            "engine": "structural-fallback",
            "conforms": not problems,
            "summary": (
                "Critical SHACL-equivalent invariants passed"
                if not problems
                else "; ".join(problems)
            ),
        }


def list_scenarios() -> list[dict[str, str]]:
    return [
        {
            "id": spec.id,
            "title": spec.title,
            "question": spec.question,
            "intent": spec.intent,
            "authority": spec.authority.value,
        }
        for spec in SCENARIOS.values()
    ]


def run_scenario(
    scenario_id: str,
    graph: Graph | None = None,
) -> ScenarioResult:
    try:
        spec = SCENARIOS[scenario_id]
    except KeyError as exc:
        raise KeyError(
            f"Unknown semantic-city scenario: {scenario_id}"
        ) from exc

    g = graph or build_demo_graph()
    validation = validate_graph(g)
    if not validation["conforms"]:
        raise ValueError(
            f"Semantic city graph is invalid: {validation['summary']}"
        )

    result = g.query(spec.query)
    rows = [
        {
            str(name): _term_to_json(value)
            for name, value in row.asdict().items()
        }
        for row in result
    ]

    evidence = [
        {
            "id": key,
            "label": value["label"],
            "publisher": value["publisher"],
            "endpoint": value["endpoint"],
            "evidence_class": value["evidence_class"],
            "caveat": value["caveat"],
        }
        for key, value in SOURCE_REGISTRY.items()
    ]

    return ScenarioResult(
        id=spec.id,
        title=spec.title,
        question=spec.question,
        authority=spec.authority.value,
        recommendation=spec.recommendation,
        caveat=spec.caveat,
        query="\n".join(
            line.rstrip()
            for line in spec.query.strip().splitlines()
        ),
        rows=rows,
        evidence=evidence,
        graph_stats={
            "triples": len(g),
            "scenario_count": len(SCENARIOS),
        },
        validation=validation,
    )


def export_turtle(graph: Graph | None = None) -> str:
    return (graph or build_demo_graph()).serialize(format="turtle")
