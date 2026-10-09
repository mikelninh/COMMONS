# CITY THREAD v0.7 · THE BRIEF

**Live after release:** https://mikelninh.github.io/COMMONS/city-thread/brief/

A small, meaningful decision game: **One fictional expert field-review slot. Three possible sites. One reasoned recommendation for investigation.**

This is a standalone new front door to CITY THREAD, with the **same warm Ivory / Indigo / Apricot visual language**. The fully functional v0.6 Ripple Lab remains at \`/city-thread/mission/\`, and the original learning atlas remains at \`/city-thread/\`.

## The experience — 3 minutes, 4 beats

1. **The Brief:** In a clearly FICTIONAL public-sector practice scenario, only one of three possible water-fountain sites can receive the next detailed field review. Pick intuitively based on one understandable metric. No real budget, grant or approval is implied.
2. **The Reveal:** The same official 2022 historical climate classification and WFS fountain data yield two other important indicators. The player learns that the highest broad sample-grid reach is **not** the same as the most points in the historically very unfavorable class or the greatest distance to the nearest documented fountain.
3. **The Choice:** Pick a priority principle, choose (or change) one candidate, name the first missing fact you would verify, and acknowledge this is a review proposal, not a construction recommendation. The candidate **does not have to be the model leader** in the chosen priority; the tradeoff is explained.
4. **The Case File:** A thoughtful, localized result—not a "perfect score." A downloadable Markdown field note and a replayable URL. **Nothing is ever submitted to a city authority, and no user data is persisted.**

## Evidence-backed trade-off, not synthetic scoring

Source geometry comes entirely from previously frozen, independently retrieved official Berlin WFS files (October 9, 2026):

- **242/242** water fountain WFS inventory points at retrieval time;
- **154/154** historic 2022 bioclimatic settlement overall appraisal polygons intersecting a small fixed Kreuzberg-area BBOX, not the whole city;
- **290** 90-m grid points lying inside the WFS settlement polygons;
- **192** of these grid points within the two selected historic "ungünstig" / "sehr ungünstig" classes;
- **126** of these selected grid points whose nearest inventoried water fountain is beyond the purely illustrative 300-m straight-line radius.

Three sample-grid-center site proposals:

| Candidate | Model grid points newly within radius | Of those: "sehr ungünstig" | Distance to nearest inventoried fountain |
| --- | ---: | ---: | ---: |
| **A: Das weite Netz** | **+24** | 7 | 529 m |
| **B: Der heissere Kern** | +21 | **10** | 529 m |
| **C: Die grössere Lücke** | +20 | 5 | **738 m** |

These are objectively different ranking criteria within a *limited* screening model. **No candidate is certified to be a good construction site.** The model does not count humans, track operating fountains, infer actual pedestrian catchments or population, predict temperature reduction, know land ownership/permits/utility feasibility, or assign construction budgets.

Even the "one field review slot" is **a fictional game premise**. It is not evidence of any real public procurement, planning commission, budget or request.

The script **recomputes all metrics** from WFS snapshots rather than trusting hardcoded values in \`candidates.json\`. When metrics disagree or snapshots are incomplete, the game refuses to proceed. The independent release checker \`scripts/city-thread-v07-verify.py\` repeats the exact geometry/scoring with Shapely to catch incorrect model code.

## Interface and interaction design

- **One mission, one clear decision**: choices change a real map and an outcome without adding a generic multi-panel dashboard.
- **Staged information**: initial intuition, true second-order geographic evidence, a priority choice and explicit human decision. The surprise is *disclosure of existing evidence*, not a fabricated "new study".
- **World feel**: selected site marker and computed links to actual newly-in-radius sample points. Source-sourced polygon geometry and optionally loaded real street-map context, clearly labeled.
- **Outcome feels earned**: shareable case file and a small "For Human Review" ritual, rather than a fake success badge.
- **Accessibility**: source-driven SVG markers support keyboard focus/Enter, text choices offer alternatives to maps, focusable headings, native dialog, reduced-motion preferences, mobile layout.
- **Privacy**: no analytics or backend submission. Local file download only; share URL carries choice, value priority and the next verification task.

## How to QA or inspect

Independent data verification:

~~~sh
python -m pip install "shapely>=2,<3" "rdflib>=7,<8" "pyshacl>=0.29,<1"
python scripts/city-thread-v07-verify.py
python scripts/city-thread-v04-verify.py
~~~

Browser testing with Playwright v1.55:

~~~sh
npm install --no-save --package-lock=false playwright@1.55.0
npx playwright install --with-deps chromium
node scripts/city-thread-v07-smoke.mjs
~~~

The production GitHub Pages workflow executes the browser suite both locally **before** deployment and on the actual public URL **after** deployment. Screenshots are retained as CI artifacts. Existing CITY THREAD and WORLD PULSE checks must remain green.

Data source links:
- https://daten.berlin.de/datensaetze/trinkwasserbrunnen-wfs-47dba2c3
- https://daten.berlin.de/datensaetze/klimabewertungskarten-2022-umweltatlas-wfs-ac0751a2

Both are used under the official **Datenlizenz Deutschland – Zero – Version 2.0**. This project is independent of Berlin, DKSR and CIVORA.

## Next decision

Before new animation or more fictional characters, run **5 unassisted usability sessions**. Measure completion, ability to explain the two-tier climate metric, willingness to reconsider the provisional choice, success in identifying unverified needs, and subjective enjoyment. Target 8/10 is a **goal, not a measured rating**. The next version should respond to what testers actually found confusing or satisfying.
