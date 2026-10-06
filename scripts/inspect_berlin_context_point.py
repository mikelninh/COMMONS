from __future__ import annotations

import json
import math
from urllib.parse import urlencode
from urllib.request import Request, urlopen

POINT = (13.4132, 52.5219)
QUERIES = {
    "justice": (
        "https://gdi.berlin.de/services/wfs/ua_umweltgerechtigkeit2023",
        "ua_umweltgerechtigkeit2023:z_gesamt_umwelt2023",
        0.0015,
        8,
    ),
    "green": (
        "https://gdi.berlin.de/services/wfs/gruenanlagen",
        "gruenanlagen:gruenanlagen",
        0.012,
        60,
    ),
    "hospitals_plan": (
        "https://gdi.berlin.de/services/wfs/krankenhaeuser",
        "krankenhaeuser:plankrankenhaeuser",
        0.04,
        50,
    ),
    "hospitals_other": (
        "https://gdi.berlin.de/services/wfs/krankenhaeuser",
        "krankenhaeuser:weitere_krankenhaeuser",
        0.04,
        50,
    ),
}


def fetch(endpoint: str, typename: str, radius: float, count: int):
    lon, lat = POINT
    dy = radius * 0.72
    params = {
        "service": "WFS",
        "version": "2.0.0",
        "request": "GetFeature",
        "typeNames": typename,
        "outputFormat": "application/json",
        "srsName": "EPSG:4326",
        "count": str(count),
        "bbox": f"{lon-radius},{lat-dy},{lon+radius},{lat+dy},EPSG:4326",
    }
    url = endpoint + "?" + urlencode(params)
    req = Request(
        url,
        headers={
            "User-Agent": "COMMONS-Semantic-City/0.5",
            "Accept": "application/json,*/*;q=0.8",
        },
    )
    with urlopen(req, timeout=30) as r:
        return json.load(r)


for key, (endpoint, typename, radius, count) in QUERIES.items():
    data = fetch(endpoint, typename, radius, count)
    features = data.get("features") or []
    print("===", key.upper(), "===")
    print("COUNT", len(features))
    for feature in features[:5]:
        print(
            "FEATURE",
            json.dumps(
                {
                    "id": feature.get("id"),
                    "properties": feature.get("properties"),
                    "geometry_type": (feature.get("geometry") or {}).get("type"),
                    "coordinates": (feature.get("geometry") or {}).get("coordinates"),
                },
                ensure_ascii=False,
            )[:5000],
        )
