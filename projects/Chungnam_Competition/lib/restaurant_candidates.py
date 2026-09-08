# -*- coding: utf-8 -*-
"""Google Places 후보와 공공 식당 API 후보 병합·중복 제거."""
from __future__ import annotations

import re
from typing import Any

from lib.distance import haversine


def _norm_name(n: str) -> str:
    return re.sub(r"\s+", "", str(n or "").lower())


def merge_restaurant_candidate_lists(
    google_places: list[dict[str, Any]],
    citytour: list[dict[str, Any]],
    ref_lat: float,
    ref_lng: float,
) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    for g in google_places:
        row = {
            **g,
            "source_type": g.get("source_type") or "google_places",
            "source_mix": "google_places",
            "merged_candidate_flag": bool(g.get("merged_candidate_flag")),
            "public_data_match": bool(g.get("public_data_match")),
        }
        merged.append(row)

    for c in citytour:
        cn = _norm_name(str(c.get("name") or ""))
        if not cn:
            continue
        try:
            clat, clng = float(c["lat"]), float(c["lng"])
        except (KeyError, TypeError, ValueError):
            continue
        dup = False
        for g in merged:
            if _norm_name(str(g.get("name") or "")) != cn:
                continue
            try:
                dkm = haversine(float(g["lat"]), float(g["lng"]), clat, clng)
            except (TypeError, ValueError):
                continue
            if dkm <= 0.15:
                dup = True
                g["merged_candidate_flag"] = True
                if g.get("source_type") == "google_places":
                    g["source_mix"] = "merged"
                    g["public_data_match"] = True
                break
        if dup:
            continue
        merged.append(
            {
                **c,
                "source_type": "citytour_api",
                "source_mix": "public_data",
                "merged_candidate_flag": False,
                "public_data_match": True,
            }
        )
    return merged
