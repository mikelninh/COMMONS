#!/usr/bin/env python3
"""CITY THREAD v0.7 — independent candidate trade-off release gate.

Validate the 3 positions used in the playful, explicitly fictional brief
against the REAL saved Berlin WFS records and original climate polygons.
These metrics are point-grid geometry, not residents or real construction feasibility.

Requires shapely>=2, installed in the existing CI pipeline.
"""
from __future__ import annotations
import json
import math
from pathlib import Path
from shapely.geometry import Point, shape

ROOT = Path(__file__).resolve().parents[1] / "public" / "city-thread"
B = (13.385,52.490,13.407,52.512)
CENTER = (B[1]+B[3])/2
M_LAT = 111132
M_LON = 111320 * math.cos(math.radians(CENTER))
STEP_LAT = 90/M_LAT
STEP_LON = 90/M_LON

def read(prefix, field):
    chunks = [json.loads((ROOT / f"{prefix}-{i}.json").read_text("utf-8")) for i in range(4)]
    assert [ch["page"] for ch in chunks] == [0,1,2,3], "Complete WFS pagination required"
    return [obj for chunk in chunks for obj in chunk[field]]

def hav(a,b):
    rad=math.pi/180
    x=(b["lat"]-a["lat"])*rad
    y=(b["lon"]-a["lon"])*rad
    h=math.sin(x/2)**2+math.cos(a["lat"]*rad)*math.cos(b["lat"]*rad)*math.sin(y/2)**2
    return 2*6371008.8*math.asin(min(1,math.sqrt(h)))

def main():
    fountains=read("fountains-all","records")
    data=read("heat","features")
    brief=json.loads((ROOT / "brief" / "candidates.json").read_text("utf-8"))
    assert len(fountains)==242==len(set(x["id"] for x in fountains))
    assert len(data)==154==len(set(x["id"] for x in data))
    assert brief["fictionalBrief"] is True
    assert [x["id"] for x in brief["candidates"]]==["A","B","C"]
    zones=[(z["heat"],shape(z["g"])) for z in data]
    assert brief["dataSource"]["hypotheticalRadiusMetres"]==300
    samples=[]
    lat=B[1]+STEP_LAT/2
    while lat<B[3]:
        lon=B[0]+STEP_LON/2
        while lon<B[2]:
            p=Point(lon,lat)
            z=next((label for label,g in zones if g.contains(p)),None)
            if z is not None:
                location={"lon":lon,"lat":lat,"heat":z}
                nearest=min(hav(location,f) for f in fountains)
                samples.append({**location,"nearest":nearest})
            lon+=STEP_LON
        lat+=STEP_LAT
    high=[x for x in samples if x["heat"] in ("ungünstig","sehr ungünstig")]
    baseline=[x for x in high if x["nearest"]>300]
    assert len(samples)==290, len(samples)
    assert len(high)==192, len(high)
    assert len(baseline)==126, len(baseline)
    results={}
    for c in brief["candidates"]:
        newly=[p for p in baseline if hav(c,p)<=300]
        nearest=min(((hav(c,f),f) for f in fountains),key=lambda pair:pair[0])
        heat_here=next((label for label,g in zones if g.contains(Point(c["lon"],c["lat"]))),"unbekannt")
        expected=c["expected"]
        assert expected["gain"]==len(newly),(c["id"],"gain",expected["gain"],len(newly))
        severe=sum(p["heat"]=="sehr ungünstig" for p in newly)
        assert expected["severe"]==severe,(c["id"],"severe",severe)
        assert abs(expected["nearestMeters"]-round(nearest[0]))<=2
        assert expected["nearestId"]==nearest[1]["id"]
        assert expected["heatClass"]==heat_here
        results[c["id"]]={"gain":len(newly),"severe":severe,"nearest":round(nearest[0])}
    assert max(results, key=lambda x:results[x]["gain"])=="A"
    assert max(results, key=lambda x:results[x]["severe"])=="B"
    assert max(results, key=lambda x:results[x]["nearest"])=="C"
    assert results["A"]["gain"]>results["B"]["gain"]>results["C"]["gain"]
    print("PASS 242 unique water WFS features; 154 unique Berlin 2022 climate polygons")
    print("PASS 290 polygon-intersecting 90m samples, 192 selected climate samples, 126 uncovered (300m baseline)")
    print("PASS A = coverage leader; B = severe-class leader; C = largest listed-fountain distance")
    for site,fields in results.items():
        print(f"PASS {site}: +{fields['gain']} newly in radius, {fields['severe']} very unfavorable, nearest {fields['nearest']} m")
    print("PASS Sources & model are verifiable; the field-visit constraint is a FICTIONAL game mechanism.")
if __name__=="__main__":main()
