from __future__ import annotations

from dataclasses import asdict
import json
import math
from time import sleep
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from commons.hypothesis_lab import BacktestPoint
from commons.scale_points import GLOBAL_POINTS


WORLDPOP_API = "https://api.worldpop.org/v2"
DEFAULT_RADIUS_KM = 20.0


def _square_polygon(point: BacktestPoint, radius_km: float) -> dict[str, Any]:
    dlat = radius_km / 111.0
    cos_lat = max(0.15, abs(math.cos(math.radians(point.latitude))))
    dlon = radius_km / (111.0 * cos_lat)
    west = point.longitude - dlon
    east = point.longitude + dlon
    south = point.latitude - dlat
    north = point.latitude + dlat
    return {
        "type": "Polygon",
        "coordinates": [[
            [west, south],
            [east, south],
            [east, north],
            [west, north],
            [west, south],
        ]],
    }


def _json_request(
    url: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    timeout: int = 45,
) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = Request(
        url,
        data=data,
        method=method,
        headers={
            "User-Agent": "COMMONS-Exposure-Lab/0.1",
            "Content-Type": "application/json",
        },
    )
    with urlopen(request, timeout=timeout) as response:  # noqa: S310
        return json.loads(response.read().decode("utf-8"))


def fetch_population(
    point: BacktestPoint,
    *,
    year: int = 2026,
    radius_km: float = DEFAULT_RADIUS_KM,
    poll_attempts: int = 30,
    poll_seconds: float = 1.0,
) -> dict[str, Any]:
    submitted = _json_request(
        f"{WORLDPOP_API}/population",
        method="POST",
        payload={
            "geojson": _square_polygon(point, radius_km),
            "year": year,
            "resolution": "1km",
        },
    )
    task_id = submitted.get("task_id")
    if not task_id:
        raise RuntimeError(f"WorldPop did not return task_id: {submitted}")

    for _ in range(poll_attempts):
        result = _json_request(f"{WORLDPOP_API}/tasks/{task_id}")
        status = result.get("status")
        if status == "success":
            data = result.get("result") or {}
            return {
                "population": round(float(data.get("total_population") or 0)),
                "area_km2": data.get("area_km2"),
                "population_density": data.get("population_density"),
                "data_year": data.get("data_year") or year,
                "data_source": data.get("data_source") or "WorldPop",
                "radius_km": radius_km,
            }
        if status == "failure":
            raise RuntimeError(str(result.get("error") or result))
        sleep(poll_seconds)
    raise TimeoutError(f"WorldPop task {task_id} did not finish in time")


def run_exposure_context(
    *,
    points: tuple[BacktestPoint, ...] = GLOBAL_POINTS,
    year: int = 2026,
    radius_km: float = DEFAULT_RADIUS_KM,
) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []

    for point in points:
        try:
            population = fetch_population(
                point,
                year=year,
                radius_km=radius_km,
            )
            results.append(
                {
                    "point": asdict(point),
                    **population,
                }
            )
        except (HTTPError, URLError, TimeoutError, OSError, RuntimeError, ValueError) as exc:
            errors.append({"point_id": point.id, "error": str(exc)})

    usable_ratio = len(results) / len(points) if points else 0.0
    status = "healthy" if usable_ratio >= 0.90 else "degraded" if usable_ratio >= 0.60 else "insufficient"

    return {
        "schema_version": "0.1",
        "source": "WorldPop API v2",
        "source_url": WORLDPOP_API,
        "year": year,
        "radius_km": radius_km,
        "coverage_status": status,
        "requested_points": len(points),
        "usable_points": len(results),
        "source_errors": errors,
        "points": results,
        "hypothesis": {
            "id": "H13",
            "claim": "Adding population exposure improves which physical hazards deserve human attention first.",
            "status": "insufficient",
            "effect": f"population context available for {len(results)}/{len(points)} locations; impact labels not yet joined",
            "product_update": (
                "Show population exposure as context only. Do not let it change ALERT or PRIORITY until historical impact-labelled validation exists."
            ),
        },
        "limitations": [
            "Population within an approximate square around a point is not the population actually exposed to a hazard.",
            "This layer does not model vulnerability, infrastructure, mobility, floodplain geometry, or impact.",
            "WorldPop population context must not be interpreted as casualties or people at risk.",
        ],
    }
