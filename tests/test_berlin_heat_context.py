from commons.berlin_heat_context import (
    BerlinHeatDecisionContext,
    JusticeRecord,
    NearbyPlaceRecord,
    build_graph,
    fetch_justice,
    fetch_nearest_green,
    fetch_nearest_hospital,
    run_cross_domain_heat,
)
from commons.berlin_heat_wfs import BerlinHeatRecord
from commons.semantic_city import CITY


def fake_json(url: str) -> dict:
    if "z_gesamt_umwelt2023" in url:
        return {
            "features": [
                {
                    "id": "justice.outside",
                    "properties": {
                        "plr_id": "outside",
                        "plr_name": "Outside",
                        "kategorie": "einfach",
                    },
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[
                            [13.50, 52.50],
                            [13.51, 52.50],
                            [13.51, 52.51],
                            [13.50, 52.51],
                            [13.50, 52.50],
                        ]],
                    },
                },
                {
                    "id": "justice.inside",
                    "properties": {
                        "plr_id": "01100310",
                        "plr_name": "Alexanderplatzviertel",
                        "kategorie": "dreifach",
                        "bioklima": "hoch",
                        "gruenvers": "mittel",
                        "laerm": "hoch",
                        "luft": "hoch",
                        "status_ind": "mittlerer Status-Index",
                        "einwohner": "unter 10.000",
                    },
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[
                            [13.40, 52.51],
                            [13.43, 52.51],
                            [13.43, 52.54],
                            [13.40, 52.54],
                            [13.40, 52.51],
                        ]],
                    },
                },
            ]
        }
    if "gruenanlagen:gruenanlagen" in url:
        return {
            "features": [
                {
                    "id": "green.far",
                    "properties": {
                        "namenr": "Far Park",
                    },
                    "geometry": {
                        "type": "Point",
                        "coordinates": [13.43, 52.53],
                    },
                },
                {
                    "id": "green.near",
                    "properties": {
                        "namenr": "Near Green",
                        "objartname": "Grünanlage",
                    },
                    "geometry": {
                        "type": "Point",
                        "coordinates": [13.414, 52.522],
                    },
                },
            ]
        }
    if "plankrankenhaeuser" in url:
        return {
            "features": [
                {
                    "id": "hospital.plan",
                    "properties": {
                        "kkh_standort": "Plan Hospital",
                        "betten_insgesamt": "415",
                    },
                    "geometry": {
                        "type": "Point",
                        "coordinates": [13.398, 52.526],
                    },
                }
            ]
        }
    if "weitere_krankenhaeuser" in url:
        return {
            "features": [
                {
                    "id": "hospital.other",
                    "properties": {
                        "name": "Closer Clinic",
                        "betten": 20,
                    },
                    "geometry": {
                        "type": "Point",
                        "coordinates": [13.4128, 52.5221],
                    },
                }
            ]
        }
    raise AssertionError(url)


def sample_heat() -> BerlinHeatRecord:
    return BerlinHeatRecord(
        feature_type="multi-layer-wfs",
        feature_id="0000000001000265",
        retrieved_at="2026-10-06T09:01:57Z",
        longitude=13.4132,
        latitude=52.5219,
        radius_m=25.0,
        match_mode="point_bbox",
        join_mode="shared_schl5",
        properties={
            "pet14h": 40.56,
            "utci14h": 36.31,
            "t2m14h": 32.82,
            "uhi": 2.18,
            "typklar": "Straße",
        },
        layers={
            metric: {
                "feature_type": f"heat:{metric}",
                "feature_id": f"{metric}.1",
                "match_mode": "point_bbox",
            }
            for metric in (
                "pet14h",
                "utci14h",
                "t2m14h",
                "uhi",
            )
        },
    )


def sample_context() -> BerlinHeatDecisionContext:
    return BerlinHeatDecisionContext(
        longitude=13.4132,
        latitude=52.5219,
        retrieved_at="2026-10-06T09:10:00Z",
        heat=sample_heat(),
        justice=JusticeRecord(
            feature_id="justice.inside",
            planning_area_id="01100310",
            planning_area_name="Alexanderplatzviertel",
            multiple_burden="dreifach",
            bioclimate="hoch",
            green_provision="mittel",
            noise="hoch",
            air="hoch",
            social_status="mittlerer Status-Index",
            population_band="unter 10.000",
            retrieved_at="2026-10-06T09:10:00Z",
            raw_properties={"kategorie": "dreifach"},
        ),
        nearest_green=NearbyPlaceRecord(
            feature_id="green.near",
            feature_type="gruenanlagen:gruenanlagen",
            name="Near Green",
            distance_m=60.0,
            properties={
                "namenr": "Near Green",
                "katasterfl": 1000,
            },
            retrieved_at="2026-10-06T09:10:00Z",
            source_endpoint="green",
        ),
        nearest_hospital=NearbyPlaceRecord(
            feature_id="hospital.other",
            feature_type=(
                "krankenhaeuser:"
                "weitere_krankenhaeuser"
            ),
            name="Closer Clinic",
            distance_m=40.0,
            properties={
                "name": "Closer Clinic",
                "betten": 20,
            },
            retrieved_at="2026-10-06T09:10:00Z",
            source_endpoint="hospital",
        ),
        green_features_within_radius=12,
        green_radius_m=1200.0,
        hospital_radius_m=4000.0,
    )


def test_justice_selects_polygon_covering_point() -> None:
    record = fetch_justice(
        13.4132,
        52.5219,
        fake_json,
    )
    assert record.planning_area_name == (
        "Alexanderplatzviertel"
    )
    assert record.multiple_burden == "dreifach"
    assert record.bioclimate == "hoch"
    assert record.green_provision == "mittel"


def test_nearest_green_and_hospital_are_geometric() -> None:
    green, count = fetch_nearest_green(
        13.4132,
        52.5219,
        fetch_json=fake_json,
    )
    hospital = fetch_nearest_hospital(
        13.4132,
        52.5219,
        fetch_json=fake_json,
    )
    assert count == 2
    assert green.feature_id == "green.near"
    assert green.distance_m < 100
    assert hospital.feature_id == "hospital.other"
    assert hospital.distance_m < 100


def test_cross_domain_graph_has_no_demo_values() -> None:
    graph = build_graph(sample_context())
    flags = [
        value.toPython()
        for value in graph.objects(
            None,
            CITY.isDemoValue,
        )
    ]
    assert flags
    assert all(flag is False for flag in flags)


def test_cross_domain_sparql_explains_without_magic_score() -> None:
    result = run_cross_domain_heat(
        sample_context()
    )
    assert result["validation"]["conforms"] is True
    assert result["rows"]
    row = result["rows"][0]
    assert row["planName"] == "Alexanderplatzviertel"
    assert row["multipleBurden"] == "dreifach"
    assert row["bioclimate"] == "hoch"
    assert row["greenProvision"] == "mittel"
    assert row["hospitalName"] == "Closer Clinic"
    assert result["graph_stats"]["synthetic_values"] == 0
    assert len(result["evidence_gaps"]) == 4
    joined = " ".join(
        item["meaning"]
        for item in result["rationale"]
    ).lower()
    assert "no new composite score" in joined


def test_cross_domain_authority_stays_human() -> None:
    result = run_cross_domain_heat(
        sample_context()
    )
    assert (
        result["authority"]
        == "human_decision_required"
    )
    assert "do not allocate resources" in (
        result["recommendation"].lower()
    )
    assert result["what_would_change_this"]
