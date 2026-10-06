from commons.semantic_city import (
    CITY,
    SCENARIOS,
    build_demo_graph,
    export_turtle,
    list_scenarios,
    run_scenario,
    validate_graph,
)


def test_semantic_city_exposes_four_reusable_scenarios() -> None:
    scenarios = list_scenarios()
    assert [item["id"] for item in scenarios] == [
        "heat",
        "resilience",
        "energy",
        "flood",
    ]
    assert all(
        item["authority"]
        in {"human_decision_required", "never_auto_execute"}
        for item in scenarios
    )


def test_graph_is_rdf_and_marks_fixture_values_as_demo() -> None:
    graph = build_demo_graph()
    assert len(graph) > 100
    demo_values = list(graph.subjects(CITY.isDemoValue, None))
    assert demo_values
    assert "@prefix city:" in export_turtle(graph)


def test_semantic_graph_passes_validation() -> None:
    result = validate_graph(build_demo_graph())
    assert result["conforms"] is True


def test_heat_scenario_returns_explainable_evidence() -> None:
    result = run_scenario("heat")
    assert result.rows
    assert float(result.rows[0]["heat"]) >= 0.70
    assert result.authority == "human_decision_required"
    assert result.evidence
    assert "illustrative" in result.caveat.lower()


def test_resilience_traverses_dependency_chain() -> None:
    result = run_scenario("resilience")
    labels = {row["label"] for row in result.rows}
    assert "Traffic signal 42 - synthetic" in labels
    assert "Hospital access route - synthetic" in labels
    assert result.authority == "never_auto_execute"


def test_energy_query_ranks_candidates_without_hiding_policy_choice() -> None:
    result = run_scenario("energy")
    assert len(result.rows) == 3
    efficiencies = [
        float(row["co2PerMillion"])
        for row in result.rows
    ]
    assert efficiencies == sorted(efficiencies, reverse=True)
    assert "policy choices" in result.caveat


def test_flood_scenario_routes_attention_not_commands() -> None:
    result = run_scenario("flood")
    assert result.rows[0]["label"] == "Care facility - synthetic"
    assert result.authority == "never_auto_execute"
    assert "operator" in result.recommendation.lower()


def test_unknown_scenario_is_rejected() -> None:
    try:
        run_scenario("magic")
    except KeyError as exc:
        assert "Unknown semantic-city scenario" in str(exc)
    else:
        raise AssertionError("Expected unknown scenario to fail")


def test_public_semantic_city_demo_exposes_provenance_and_truth_boundary() -> None:
    from pathlib import Path

    page = Path("public/semantic-city.html").read_text(
        encoding="utf-8"
    )
    script = Path("public/semantic-city.js").read_text(
        encoding="utf-8"
    )
    assert "Ask the city" in page
    assert "SHOW FULL PROVENANCE" in page
    assert "Truth boundary" in page
    for scenario in SCENARIOS:
        assert f'data-scenario="{scenario}"' in page
        assert f"{scenario}:" in script


def test_semantic_city_assets_have_valid_javascript_when_node_is_available() -> None:
    from pathlib import Path
    import shutil
    import subprocess

    node = shutil.which("node")
    if node is None:
        return
    subprocess.run(
        [node, "--check", str(Path("public/semantic-city.js"))],
        check=True,
    )
