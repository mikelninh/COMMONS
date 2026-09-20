from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from commons.hypothesis_lab import BacktestPoint, build_records


GLOBAL_POINTS: tuple[BacktestPoint, ...] = (
    BacktestPoint("nuwakot", "Nuwakot", "Nepal", 27.95, 85.18),
    BacktestPoint("manila", "Manila", "Philippines", 14.60, 120.98),
    BacktestPoint("delhi", "Delhi", "India", 28.61, 77.21),
    BacktestPoint("warsaw", "Warsaw", "Poland", 52.23, 21.01),
    BacktestPoint("niamey", "Niamey", "Niger", 13.51, 2.11),
    BacktestPoint("dhaka", "Dhaka", "Bangladesh", 23.81, 90.41),
    BacktestPoint("mumbai", "Mumbai", "India", 19.08, 72.88),
    BacktestPoint("chennai", "Chennai", "India", 13.08, 80.27),
    BacktestPoint("bangkok", "Bangkok", "Thailand", 13.76, 100.50),
    BacktestPoint("hanoi", "Hanoi", "Vietnam", 21.03, 105.85),
    BacktestPoint("jakarta", "Jakarta", "Indonesia", -6.21, 106.85),
    BacktestPoint("singapore", "Singapore", "Singapore", 1.35, 103.82),
    BacktestPoint("osaka", "Osaka", "Japan", 34.69, 135.50),
    BacktestPoint("brisbane", "Brisbane", "Australia", -27.47, 153.03),
    BacktestPoint("auckland", "Auckland", "New Zealand", -36.85, 174.76),
    BacktestPoint("nairobi", "Nairobi", "Kenya", -1.29, 36.82),
    BacktestPoint("lagos", "Lagos", "Nigeria", 6.52, 3.38),
    BacktestPoint("accra", "Accra", "Ghana", 5.56, -0.19),
    BacktestPoint("cape-town", "Cape Town", "South Africa", -33.92, 18.42),
    BacktestPoint("cairo", "Cairo", "Egypt", 30.04, 31.24),
    BacktestPoint("istanbul", "Istanbul", "Türkiye", 41.01, 28.98),
    BacktestPoint("berlin", "Berlin", "Germany", 52.52, 13.41),
    BacktestPoint("london", "London", "United Kingdom", 51.51, -0.13),
    BacktestPoint("rome", "Rome", "Italy", 41.90, 12.50),
    BacktestPoint("new-york", "New York", "United States", 40.71, -74.01),
    BacktestPoint("miami", "Miami", "United States", 25.76, -80.19),
    BacktestPoint("houston", "Houston", "United States", 29.76, -95.37),
    BacktestPoint("mexico-city", "Mexico City", "Mexico", 19.43, -99.13),
    BacktestPoint("recife", "Recife", "Brazil", -8.05, -34.88),
    BacktestPoint("buenos-aires", "Buenos Aires", "Argentina", -34.60, -58.38),
)


def build_global_records(
    *,
    start_date: str,
    end_date: str,
    points: tuple[BacktestPoint, ...] = GLOBAL_POINTS,
    max_workers: int = 5,
) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    """Fetch locations concurrently while keeping source failures explicit.

    Each worker handles one point so at most max_workers locations hit the
    upstream APIs at once. The shared per-run HTTP cache remains effective
    across H20/H21/H22.
    """
    records_by_id: dict[str, list[dict[str, Any]]] = {}
    errors_by_id: dict[str, list[dict[str, str]]] = {}

    def fetch(point: BacktestPoint):
        return point.id, build_records(
            start_date=start_date,
            end_date=end_date,
            points=(point,),
        )

    workers = max(1, min(max_workers, len(points)))
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(fetch, point): point for point in points}
        for future in as_completed(futures):
            point = futures[future]
            try:
                point_id, (records, errors) = future.result()
            except Exception as exc:
                point_id = point.id
                records = []
                errors = [
                    {
                        "point": point.id,
                        "source": "global_fetch",
                        "error": str(exc),
                    }
                ]
            records_by_id[point_id] = records
            errors_by_id[point_id] = errors

    records: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    for point in points:
        records.extend(records_by_id.get(point.id, []))
        errors.extend(errors_by_id.get(point.id, []))
    return records, errors


def full_council_records(
    records: list[dict[str, Any]],
    *,
    expected_models: int = 3,
) -> list[dict[str, Any]]:
    return [
        record
        for record in records
        if len(record.get("predictions_mm") or {}) == expected_models
    ]
