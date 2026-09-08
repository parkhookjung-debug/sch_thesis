# -*- coding: utf-8 -*-
"""
한국환경공단 에어코리아 — 시도별 실시간 대기질 (공공데이터포털)

scoring.py 의 dust(1~4)는 PM2.5 농도 구간으로 환산한다.
실시간 관측이 아닌 측정망 기반 값이며, 통신 실패 시 None 반환.
"""
from __future__ import annotations

import re
from typing import Any

from lib.config import request_get, settings


def _parse_float(val: Any) -> float | None:
    if val is None:
        return None
    s = str(val).strip()
    if s in ("", "-", "측정불가"):
        return None
    m = re.match(r"^([\d.]+)", s)
    if not m:
        return None
    try:
        return float(m.group(1))
    except ValueError:
        return None


def pm25_to_grade(pm25: float) -> int:
    """PM2.5(㎍/㎥) → dust 1~4 (통합환경정책 국내 일반 구간 근사)."""
    if pm25 <= 15:
        return 1
    if pm25 <= 35:
        return 2
    if pm25 <= 75:
        return 3
    return 4


def pm10_to_grade(pm10: float) -> int:
    """PM10 기반 보조 등급 (PM2.5 없을 때)."""
    if pm10 <= 30:
        return 1
    if pm10 <= 80:
        return 2
    if pm10 <= 150:
        return 3
    return 4


def _normalize_items(body: dict) -> list[dict]:
    items = body.get("items")
    if items is None:
        return []
    if isinstance(items, list):
        return items
    if isinstance(items, dict):
        it = items.get("item")
        if it is None:
            return []
        if isinstance(it, list):
            return it
        return [it]
    return []


def fetch_air_quality_sido(sido_name: str = "충남") -> dict | None:
    """
    시도명(예: 충남, 서울) 단위 실시간 측정값을 모아 PM2.5 평균 → 등급 산출.
    실패 시 None.
    """
    key = settings.air_korea_api_key
    if not key:
        return None

    params = {
        "serviceKey": key,
        "returnType": "json",
        "numOfRows": 200,
        "pageNo": 1,
        "sidoName": sido_name,
        "ver": "1.0",
    }
    try:
        r = request_get(
            settings.air_ctprvn_url,
            params=params,
            timeout=12,
            verify=settings.requests_ssl_verify,
        )
        r.raise_for_status()
        data = r.json()
    except Exception:
        return None

    try:
        header = data.get("response", {}).get("header", {})
        if str(header.get("resultCode", "")).strip() not in ("00", "0"):
            return None
        body = data["response"]["body"]
    except (KeyError, TypeError):
        return None

    rows = _normalize_items(body)
    pm25_list: list[float] = []
    pm10_list: list[float] = []
    for row in rows:
        v = _parse_float(row.get("pm25Value") or row.get("pm25value"))
        if v is not None:
            pm25_list.append(v)
        v10 = _parse_float(row.get("pm10Value") or row.get("pm10value"))
        if v10 is not None:
            pm10_list.append(v10)

    if not pm25_list and not pm10_list:
        return None

    pm25_avg = sum(pm25_list) / len(pm25_list) if pm25_list else None
    pm10_avg = sum(pm10_list) / len(pm10_list) if pm10_list else None

    if pm25_avg is not None:
        grade = pm25_to_grade(pm25_avg)
        basis = "pm25"
    elif pm10_avg is not None:
        grade = pm10_to_grade(pm10_avg)
        basis = "pm10"
    else:
        return None

    return {
        "dust": grade,
        "pm25": round(pm25_avg, 1) if pm25_avg is not None else None,
        "pm10": round(pm10_avg, 1) if pm10_avg is not None else None,
        "sido_name": sido_name,
        "stations_used": len(pm25_list) or len(pm10_list),
        "grade_basis": basis,
    }


def air_quality_for_city(city: str) -> dict | None:
    """프로토타입 범위는 충청남도 시군만 다루므로 시도는 항상 '충남'."""
    _ = city
    return fetch_air_quality_sido("충남")
