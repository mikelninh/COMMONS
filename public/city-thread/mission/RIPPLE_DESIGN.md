# CITY THREAD v0.6 — THE RIPPLE + SCENARIO DUEL

## Why this version

In v0.5 the visitor could move one hypothetical water fountain, and the spatial model would update. The calculations were correct, but the most interesting information was buried in a numeric counter. v0.6 makes the spatial relationships **visible and felt** without fabricating impact.

This is still an independent open civic learning prototype: **not a Berlin authority service, not DKSR/CIVORA, not a building recommendation.**

## Interaction contract

1. **The Ripple**: when a user places or releases a proposed fountain, draw subtle animated lines **only** between the proposed position and actually computed, newly in-radius 90-m model grid points. To protect performance, visual lines are capped at 46 while the displayed number is the exact total. The circle animation represents the chosen *hypothetical straight-line radius*, not an actual walking catchment, a temperature reduction or people served.
2. **Scenario Duel**: pressing “Zweiten Ort vergleichen” creates position B and lets the user select and drag A or B. Each gain is calculated independently against the **same existing 242 fountain inventory baseline** with the **same** assumed radius. Neither proposal is ever silently counted as existing infrastructure in the other's result. On the map both are visible; only the active site's lines are highlighted. The verdict reports a model point difference, not a real-world winner.
3. **Before / After**: before hides all hypothetical proposals, reach rings and newly highlighted grid points. After restores the selected scenario and its second location. Results are not manipulated by switching display modes.
4. **Share**: a URL retains both coordinates, active slot and radius for reproducible comparisons. Existing solo URLs with just \`lon\`, \`lat\` and \`radius\` remain supported.
5. **Report**: if Duel is active, the local Markdown report includes A and B coordinates, scores and the shared baseline caveat. Explicit human acknowledgment is still required. No submission occurs.
6. **Optional sound**: user-initiated, off by default, synthesised locally without an external library. Reduced-motion preference disables decorative animations.

## Evidence boundaries

The input sources remain unchanged from v0.4:

- 242 documented water fountain records from Berlin's WFS, snapshot 9 October 2026, not necessarily currently operating.
- 154 polygons intersecting a small Kreuzberg study area from the 2022 *overall bioclimatic settlement assessment* WFS (historical planning appraisal, not live heat readings).
- A 90 m point sample grid; points are not people.
- Haversine straight-line distances from grid points to listed fountains; no pedestrian routing, accessibility, permissions, land use, water supply feasibility or construction cost.

**What +24 means:** in the illustrative default scenario, 24 previously out-of-range grid points on areas with one of the selected historical bioclimatic classifications would fall inside the assumed straight-line radius of one hypothetical fountain. This is a useful hypothesis for further examination, not public policy advice.

## Technical separation and verification

- \`public/city-thread/mission/mission.js\` owns authoritative geometry loading, grid construction, source provenance, metric calculations, user proposal and baseline.
- \`public/city-thread/mission/ripple.js\` owns interaction-only presentation: linking actual model sample points, A/B state, comparative scores, optional audio, share URL additions and report additions.
- \`scripts/city-thread-v06-smoke.mjs\`: dedicated Chromium desktop and mobile tests for real connections, independent A/B baselines, interactive duel, before/after state, URL roundtrip, report acknowledgment, reduced-width layout. Existing v0.4 spatial, RDFLib SPARQL and pySHACL release checks remain in place.

To reproduce the exact geospatial/SHACL verification:
\`\`\`sh
python -m pip install "rdflib>=7,<8" "pyshacl>=0.29,<1" "shapely>=2,<3"
python scripts/city-thread-v04-verify.py
\`\`\`

The live app runs geospatial proximity calculations client-side, while true RDFLib SPARQL and pySHACL run in CI/test rather than behind a visitor-facing arbitrary query endpoint. There is no persistence, authorization or real municipal workflow.

## Next experiment

Before adding new visual layers: let 5 testers use the mission without instruction. Measure ability to place A and B, correctly articulate what the A/B comparison means, understand that the scene represents assumptions, and distinguish the model result from an official infrastructure recommendation.
