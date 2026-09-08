# -*- coding: utf-8 -*-
"""
도시관광(공공) 식당 API 클라이언트 — 엔드포인트·필드는 기관마다 달라 휴리스틱 파싱.
키·BASE URL 미설정 시 빈 목록.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
import time
from typing import Any

from lib.config import request_get, settings
from lib.distance import haversine

_CACHE: dict[str, tuple[float, list[dict[str, Any]]]] = {}
_CACHE_TTL = 900


def _cache_key(lat: float, lng: float) -> str:
    h = hashlib.sha256(
        f"{settings.citytour_restaurant_base_url}|{settings.citytour_restaurant_path}|{round(lat,4)},{round(lng,4)}".encode()
    ).hexdigest()[:24]
    return h


def _as_float(x: Any) -> float | None:
    try:
        if x is None or x == "":
            return None
        return float(str(x).replace(",", "."))
    except (TypeError, ValueError):
        return None


def _pick_str(d: dict[str, Any], *keys: str) -> str:
    for k in keys:
        if k in d and d[k] not in (None, ""):
            return str(d[k]).strip()
    return ""


def _items_from_json(data: Any) -> list[dict[str, Any]]:
    """공공데이터 JSON / 단순 배열 등에서 dict 목록 추출."""
    if data is None:
        return []
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    if not isinstance(data, dict):
        return []

    for path in (
        ("data",),
        ("items",),
        ("body", "items", "item"),
        ("response", "body", "items", "item"),
        ("result", "items"),
    ):
        cur: Any = data
        ok = True
        for p in path:
            if not isinstance(cur, dict) or p not in cur:
                ok = False
                break
            cur = cur[p]
        if not ok:
            continue
        if isinstance(cur, list):
            return [x for x in cur if isinstance(x, dict)]
        if isinstance(cur, dict):
            return [cur]
    for v in data.values():
        if isinstance(v, list) and v and isinstance(v[0], dict):
            return [x for x in v if isinstance(x, dict)]
    return []


def _normalize_api_item(raw: dict[str, Any], idx: int) -> dict[str, Any] | None:
    name = _pick_str(raw, "name", "BIZ_NM", "bizNm", "restaurantName", "업소명", "상호", "TITLE", "title")
    if not name:
        return None

    rid = _pick_str(raw, "id", "seq", "restaurantId", "관광지식별자", "일련번호")
    if not rid:
        rid = f"row{idx}"

    addr = _pick_str(raw, "address", "addr", "roadAddr", "지번주소", "도로명주소", "주소", "ADD1")
    city = _pick_str(raw, "city", "sido", "시도", "ctprvn")
    district = _pick_str(raw, "district", "sigungu", "시군구", "signgu")

    lat = _as_float(
        _pick_str(raw, "lat", "latitude", "mapY", "MAPY", "y", "위도") or None
    )
    lng = _as_float(
        _pick_str(raw, "lng", "lon", "longitude", "mapX", "MAPX", "x", "경도") or None
    )
    # 일부 API: mapX=경도, mapY=위도 (문자열 정수 스케일)
    if lat is None and raw.get("mapY") not in (None, ""):
        v = _as_float(raw.get("mapY"))
        if v is not None and v > 90:
            lat = v / 1_000_000.0
        elif v is not None:
            lat = v
    if lng is None and raw.get("mapX") not in (None, ""):
        v = _as_float(raw.get("mapX"))
        if v is not None and abs(v) > 180:
            lng = v / 1_000_000.0
        elif v is not None:
            lng = v

    cat = _pick_str(raw, "category", "type", "업종", "식당유형")
    desc = _pick_str(raw, "description", "overview", "소개", "설명")
    tags_s = _pick_str(raw, "tags", "tag", "키워드")
    tags = [t.strip() for t in re.split(r"[,;|/]", tags_s) if t.strip()][:16] if tags_s else []

    return {
        "source": "citytour_api",
        "id": str(rid),
        "name": name,
        "city": city,
        "district": district,
        "address": addr,
        "lat": lat,
        "lng": lng,
        "category": cat,
        "description": desc,
        "tags": tags,
        "raw_record": raw,
    }


def _to_place_candidate(norm: dict[str, Any]) -> dict[str, Any]:
    lat = norm.get("lat")
    lng = norm.get("lng")
    if lat is None or lng is None:
        return {}
    return {
        "place_id": f"citytour:{norm['id']}",
        "name": norm["name"],
        "address": norm.get("address") or "",
        "rating": 0.0,
        "review_count": 0,
        "open_now": None,
        "photo_url": None,
        "types": ["restaurant"] if "cafe" not in norm.get("name", "").lower() else ["cafe", "restaurant"],
        "lat": float(lat),
        "lng": float(lng),
        "source_type": "citytour_api",
        "source_mix": "public_data",
        "merged_candidate_flag": False,
        "public_data_match": True,
    }


def fetch_citytour_restaurant_candidates(
    lat: float,
    lng: float,
    *,
    max_results: int = 18,
    radius_km: float = 18.0,
) -> list[dict[str, Any]]:
    if not settings.citytour_restaurant_api_key or not settings.citytour_restaurant_base_url:
        return []

    ck = _cache_key(lat, lng)
    now = time.time()
    if ck in _CACHE and now - _CACHE[ck][0] < _CACHE_TTL:
        return _CACHE[ck][1]

    base = settings.citytour_restaurant_base_url.rstrip("/")
    path = (settings.citytour_restaurant_path or "").strip("/")
    url = f"{base}/{path}" if path else base

    params: dict[str, Any] = dict(settings.citytour_restaurant_extra_params or {})
    key_name = settings.citytour_restaurant_key_param or "serviceKey"
    params[key_name] = settings.citytour_restaurant_api_key
    if settings.citytour_restaurant_send_coords:
        params.setdefault("mapX", lng)
        params.setdefault("mapY", lat)
        params.setdefault("radius", int(radius_km * 1000))

    out: list[dict[str, Any]] = []

    # Fast DNS pre-check: skip entirely if hostname unreachable (saves 30-60s)
    try:
        from urllib.parse import urlparse
        import socket
        parsed_host = urlparse(url).hostname or ""
        if parsed_host:
            socket.setdefaulttimeout(2.0)
            try:
                socket.getaddrinfo(parsed_host, None)
            except (socket.gaierror, OSError):
                if settings.debug:
                    print(f"[citytour] DNS lookup failed for {parsed_host} — skipping", file=sys.stderr)
                _CACHE[ck] = (now, [])
                return []
            finally:
                socket.setdefaulttimeout(None)
    except Exception:
        pass

    try:
        r = request_get(url, params=params, timeout=(3, 5), verify=settings.requests_ssl_verify)
        if not r.ok:
            if settings.debug:
                print(f"[citytour] HTTP {r.status_code}", file=sys.stderr)
            _CACHE[ck] = (now, [])
            return []
        data = r.json()
    except Exception as e:
        if settings.debug:
            print(f"[citytour] {e}", file=sys.stderr)
        _CACHE[ck] = (now, [])
        return []

    items = _items_from_json(data)
    norms: list[dict[str, Any]] = []
    for i, it in enumerate(items):
        n = _normalize_api_item(it, i)
        if n:
            norms.append(n)

    for n in norms:
        cand = _to_place_candidate(n)
        if not cand:
            continue
        try:
            km = haversine(lat, lng, float(cand["lat"]), float(cand["lng"]))
        except (TypeError, ValueError):
            continue
        if km > radius_km + 2:
            continue
        out.append(cand)
        if len(out) >= max_results:
            break

    _CACHE[ck] = (now, out)
    return out
