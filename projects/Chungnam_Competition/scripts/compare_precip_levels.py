# -*- coding: utf-8 -*-
"""동일 조건에서 강수 확률만 바꿔 top_course·실내/야외 비중 비교 (개발 검증용)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.course_units import indoor_outdoor_balance  # noqa: E402
from lib.daytrip_planner import build_daytrip_payload  # noqa: E402
from lib.intent_normalize import normalize_intent  # noqa: E402
from lib.distance import haversine  # noqa: E402
from lib.recommend import match_from_api  # noqa: E402


def _route_km(places: list) -> float:
    if len(places) < 2:
        return 0.0
    t = 0.0
    for i in range(len(places) - 1):
        a = places[i].get("coords") or {}
        b = places[i + 1].get("coords") or {}
        t += haversine(
            float(a.get("lat") or 0),
            float(a.get("lng") or 0),
            float(b.get("lat") or 0),
            float(b.get("lng") or 0),
        )
    return round(t, 2)


def run(pp: float) -> dict:
    weather = {
        "temp": 22,
        "precip_prob": pp,
        "sky": 1,
        "sky_text": "맑음",
        "dust": 1,
        "hour": 14,
    }
    intent = normalize_intent("solo", "healing", "half-day", "car")
    tn = max(40, 72) if pp >= 48 else 40
    mr = match_from_api(weather, "아산", top_n=tn, intent=intent)
    payload = build_daytrip_payload(weather=weather, match_result=mr, intent=intent)
    top = payload.get("top_course") or {}
    steps = top.get("steps") or []
    names = [str(s.get("name") or "") for s in steps]
    cats = []
    for s in steps:
        nm = s.get("name")
        row = next((r for r in payload.get("recommendations", []) if r.get("name") == nm), {})
        cats.append(str(row.get("category") or s.get("category") or "?"))
    places_for_balance = [{"category": c} for c in cats]
    return {
        "precip_prob": pp,
        "top_names": names,
        "categories": cats,
        "balance": indoor_outdoor_balance(places_for_balance),
        "internal_route_km": _route_km(
            [
                {
                    "coords": next(
                        (
                            r.get("coords")
                            for r in payload.get("recommendations", [])
                            if r.get("name") == n
                        ),
                        {},
                    )
                }
                for n in names
            ]
        ),
        "summary_headline": (payload.get("summary") or {}).get("headline"),
        "summary_one_liner": (payload.get("summary") or {}).get("one_liner"),
        "weather_fit": top.get("weather_fit"),
    }


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
    levels = [10.0, 30.0, 50.0, 60.0, 80.0]
    rows = [run(pp) for pp in levels]
    print(json.dumps(rows, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
