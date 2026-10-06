from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

ENDPOINTS = {
    "justice": "https://gdi.berlin.de/services/wfs/ua_umweltgerechtigkeit2023",
    "green": "https://gdi.berlin.de/services/wfs/gruenanlagen",
    "hospitals": "https://gdi.berlin.de/services/wfs/krankenhaeuser",
}


def local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].split(":")[-1]


def get(url: str) -> bytes:
    req = Request(
        url,
        headers={
            "User-Agent": "COMMONS-Semantic-City/0.5",
            "Accept": "application/xml,text/xml,*/*;q=0.8",
        },
    )
    with urlopen(req, timeout=30) as r:
        return r.read()


def url(endpoint: str, params: dict[str, str]) -> str:
    return endpoint + "?" + urlencode(params)


def feature_types(endpoint: str) -> list[str]:
    root = ET.fromstring(
        get(
            url(
                endpoint,
                {
                    "SERVICE": "WFS",
                    "VERSION": "2.0.0",
                    "REQUEST": "GetCapabilities",
                },
            )
        )
    )
    out = []
    for ft in root.iter():
        if local(ft.tag) != "FeatureType":
            continue
        for child in ft:
            if local(child.tag) == "Name" and child.text:
                out.append(child.text.strip())
                break
    return out


def fields(endpoint: str, ft: str) -> list[str]:
    root = ET.fromstring(
        get(
            url(
                endpoint,
                {
                    "SERVICE": "WFS",
                    "VERSION": "2.0.0",
                    "REQUEST": "DescribeFeatureType",
                    "TYPENAMES": ft,
                },
            )
        )
    )
    return sorted(
        {
            str(el.attrib["name"])
            for el in root.iter()
            if local(el.tag) == "element"
            and el.attrib.get("name")
        }
    )


for key, endpoint in ENDPOINTS.items():
    print(f"=== {key.upper()} ===")
    types = feature_types(endpoint)
    print("FEATURE_TYPES", types)
    with ThreadPoolExecutor(max_workers=min(8, max(1, len(types)))) as pool:
        futs = {pool.submit(fields, endpoint, ft): ft for ft in types}
        for future in as_completed(futs):
            ft = futs[future]
            try:
                fs = future.result()
            except Exception as exc:
                print("SCHEMA_ERROR", ft, repr(exc))
                continue
            print("SCHEMA", ft, fs)
