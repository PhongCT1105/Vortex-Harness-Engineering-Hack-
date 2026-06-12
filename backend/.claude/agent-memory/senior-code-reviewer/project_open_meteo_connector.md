---
name: project-open-meteo-connector
description: Key facts about open_meteo_connector.py — architecture, thresholds, and a boundary subtlety discovered during review
metadata:
  type: project
---

open_meteo_connector.py is a drop-in replacement for jua_connector.py hitting the Open-Meteo free API. No HTTP routes of its own; no OpenAPI spec applies — validate against function contracts.

**Severity threshold subtlety (confirmed correct):**
wind=90.0 km/h produces severity="minor", NOT "ok". The logic checks `wind > 90` (severe) then `elif wind > 60` (minor); 90.0 is not > 90 so it falls to the elif which fires since 90 > 60. Any test must account for this.

**Thresholds:**
- wind > 90 km/h → severe
- wind > 60 km/h → minor (includes 60 < wind <= 90)
- precip > 10 mm/hr → minor
- temp < 268 K → minor
- two+ minors → moderate
- severe overrides all

**Testing framework:** pytest (installed in newvenv at project root), Python 3.14.
**Test file:** backend/test_open_meteo_connector.py — 54 tests, all passing as of 2026-06-12.

**Why:** Needed to document the wind=90 boundary subtlety so future tests don't repeat the same wrong assumption.
**How to apply:** When writing or reviewing severity tests, remember wind=90 is minor not ok; only wind>90 is severe.
