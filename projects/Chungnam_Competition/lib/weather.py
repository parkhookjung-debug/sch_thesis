# -*- coding: utf-8 -*-
"""
기상청 단기예보 API 연동
docs: https://www.data.go.kr/data/15084084/openapi.do
"""
import math
import os
import re
import urllib.parse

from datetime import datetime, timedelta

from lib.airquality import air_quality_for_city
from lib.config import request_get, settings

# 충남 주요 지역 격자 좌표 (위경도 → X/Y 격자)
GRID_COORDS = {
    "아산": {"nx": 67, "ny": 100},
    # 천안은 동쪽으로 격자가 달라짐(아산과 동일하면 예보가 똑같이 나옴)
    "천안": {"nx": 63, "ny": 110},
    "공주": {"nx": 63, "ny": 96},
    "보령": {"nx": 54, "ny": 91},
    "서산": {"nx": 51, "ny": 103},
    "논산": {"nx": 62, "ny": 92},
    "계룡": {"nx": 65, "ny": 95},
    "당진": {"nx": 54, "ny": 105},
    "태안": {"nx": 48, "ny": 100},
    "홍성": {"nx": 55, "ny": 98},
    "부여": {"nx": 60, "ny": 91},
    "금산": {"nx": 69, "ny": 88},
    "서천": {"nx": 55, "ny": 87},
    "예산": {"nx": 58, "ny": 99},
    "청양": {"nx": 59, "ny": 94},
}

# 충남 시군 대표 좌표(격자 선택용): GPS가 오면 가장 가까운 시군의 nx·ny 격자를 사용
CITY_ANCHORS_DEG: dict[str, tuple[float, float]] = {
    "아산": (36.7898, 127.0022),
    "천안": (36.8151, 127.1139),
    "공주": (36.4556, 127.1240),
    "보령": (36.3333, 126.6128),
    "서산": (36.7817, 126.4529),
    "논산": (36.1872, 127.0987),
    "계룡": (36.2758, 127.2386),
    "당진": (36.8897, 126.6459),
    "태안": (36.7528, 126.2983),
    "홍성": (36.6009, 126.6650),
    "부여": (36.2758, 126.9108),
    "금산": (36.1088, 127.4889),
    "서천": (36.0786, 126.6919),
    "예산": (36.6807, 126.8449),
    "청양": (36.4462, 126.8018),
}


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """대략 거리(km)."""
    r_km = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r_km * math.asin(min(1.0, math.sqrt(a)))


def _nearest_anchor_city(lat: float, lng: float) -> str:
    best = "아산"
    best_d = 1e9
    for city, (clat, clng) in CITY_ANCHORS_DEG.items():
        if city not in GRID_COORDS:
            continue
        d = _haversine_km(lat, lng, clat, clng)
        if d < best_d:
            best_d = d
            best = city
    return best


def _resolve_forecast_anchor_city(
    city: str,
    user_lat: float | None,
    user_lng: float | None,
) -> tuple[str, str]:
    """
    단기예보 격자(nx/ny)에 쓸 시군 키와 이유 태그.
    """
    if user_lat is not None and user_lng is not None:
        try:
            la = float(user_lat)
            ln = float(user_lng)
            grid_city = _nearest_anchor_city(la, ln)
            return grid_city, "gps_nearest"
        except (TypeError, ValueError):
            pass
    c = (city or "").strip()
    if c and c != "전체" and c in GRID_COORDS:
        return c, "selected_city"
    return "아산", "default_city"


def _forecast_from_items(items: list, now_hour: int) -> tuple[dict[str, str], str | None]:
    """
    단기예보 item 목록에서 현재 시각에 가장 가까운 fcstTime 슬롯의 category→값 맵 생성.
    정확히 현재 시각만 고르면, API가 내준 fcstTime이 한 시간씩 건너뛰는 경우 TMP 등이 비어 20도 기본값이 된다.
    """
    by_time: dict[str, dict[str, str]] = {}
    for item in items:
        ft = item.get("fcstTime")
        cat = item.get("category")
        if not ft or not cat:
            continue
        by_time.setdefault(ft, {})[cat] = item.get("fcstValue", "")

    if not by_time:
        return {}, None

    # 현재 시각(시)을 4자리 정수와 비교: 14시 → 1400
    target = now_hour * 100

    def time_key(ft: str) -> int:
        try:
            return int(ft)
        except (TypeError, ValueError):
            return 0

    # 가장 가까운 발표 슬롯(절대 차 최소)
    best_ft = min(by_time.keys(), key=lambda ft: abs(time_key(ft) - target))
    return by_time.get(best_ft, {}), best_ft


def get_base_time() -> tuple[str, str]:
    """기상청 API 기준 시각 계산 (30분 단위 발표)"""
    now = datetime.now()
    # 발표 시각: 0200, 0500, 0800, 1100, 1400, 1700, 2000, 2300
    base_hours = [2, 5, 8, 11, 14, 17, 20, 23]

    # 현재 시각보다 이전인 가장 최근 발표 시각 선택
    hour = now.hour
    base_hour = max([h for h in base_hours if h <= hour], default=23)

    if base_hour > hour:  # 자정 이후 케이스
        now -= timedelta(days=1)
        base_hour = 23

    base_date = now.strftime("%Y%m%d")
    base_time = f"{base_hour:02d}00"
    return base_date, base_time


def _sanitize_fallback_note(reason: str) -> str:
    """
    예외 문자열에 포함된 전체 URL·serviceKey가 UI에 노출되지 않도록 정리.
    (requests HTTPError는 'for url: ...serviceKey=...' 형태로 키가 들어감)
    """
    if not reason:
        return ""
    r = reason.strip()
    low = r.lower()
    if (
        "certificate_verify_failed" in low
        or "sslcertverificationerror" in low.replace(" ", "")
        or ("ssl" in low and "certificate" in low)
        or "certificate verify failed" in low
    ):
        return (
            "HTTPS 인증서 검증 실패로 기상청 단기예보를 받지 못했습니다. "
            "관리: certifi·SSL 루트 인증서·회사망 프록시를 점검하세요."
        )
    if re.search(r"\b403\b", r) or "Forbidden" in r:
        return (
            "공공데이터포털(data.go.kr)에서 「기상청_단기예보」 "
            "(VilageFcstInfoService) 활용신청이 승인됐는지 확인하고, "
            "호출 IP 제한을 켠 경우 현재 접속 IP를 등록했는지 확인하세요."
        )
    if "for url:" in low:
        head = r[: low.index("for url:")].strip()
        return f"{head} (요청 URL·인증키는 보안상 생략)"
    r = re.sub(r"serviceKey=[^&\s]+", "serviceKey=***", r, flags=re.IGNORECASE)
    r = re.sub(r"https?://[^\s]+", "[URL 생략]", r)
    return r[:400]


def _apply_air_quality(out: dict, city: str) -> dict:
    """에어코리아 연동(실패 시 out의 dust 등 유지)."""
    air = air_quality_for_city(city)
    if air:
        out["dust"] = air["dust"]
        out["pm25"] = air.get("pm25")
        out["pm10"] = air.get("pm10")
        out["air_source"] = (
            f"에어코리아 {air.get('sido_name')} "
            f"측정소 {air.get('stations_used')}개 기준 "
            f"({air.get('grade_basis')})"
        )
    return out


def _fallback_weather(city: str, reason: str) -> dict:
    """기상청 실패·키 없음 시에도 추천 API가 돌아가도록 하는 보수적 기본값."""
    now = datetime.now()
    out: dict = {
        "temp":        20.0,
        "precip_prob": 0.0,
        "sky":         1,
        "hour":        now.hour,
        "city":        city,
        "base_date":   now.strftime("%Y%m%d"),
        "base_time":   "0500",
        "fcst_time_slot": None,
        "dust":        1,
        "pm25":        None,
        "pm10":        None,
        "air_source":  None,
        "weather_fallback": True,
        "weather_fallback_note": _sanitize_fallback_note(reason),
        "weather_source": "fallback",
    }
    return _apply_air_quality(out, city)


def _fetch_weather_via_bridge(
    base_url: str,
    city: str,
    user_lat: float | None,
    user_lng: float | None,
) -> dict | None:
    """
    Node 게이트웨이 등 로컬 HTTP에서 단기예보 dict(JSON)를 받습니다.
    실패 시 None → 아래에서 기존 Python 경로로 재시도합니다.

    최대 2회 재시도(1초 간격)하여 게이트웨이 기동 직후 타이밍 이슈를 완화합니다.
    """
    import time as _time

    root = base_url.strip().rstrip("/")
    qd: dict[str, str] = {"city": (city or "아산").strip() or "아산"}
    if user_lat is not None:
        try:
            qd["user_lat"] = str(float(user_lat))
        except (TypeError, ValueError):
            pass
    if user_lng is not None:
        try:
            qd["user_lng"] = str(float(user_lng))
        except (TypeError, ValueError):
            pass
    url = f"{root}/__weather_raw__?{urllib.parse.urlencode(qd)}"

    max_tries = 3
    for attempt in range(max_tries):
        try:
            r = request_get(url, timeout=12)
            r.raise_for_status()
            data = r.json()
            if not isinstance(data, dict):
                return None
            # 에러 바디 {detail: ...} 등 배제
            if "temp" not in data:
                return None
            return data
        except Exception as exc:
            if settings.debug:
                print(
                    f"[weather-bridge] attempt {attempt + 1}/{max_tries} failed: {exc}",
                    file=__import__("sys").stderr,
                )
            if attempt < max_tries - 1:
                _time.sleep(1.0)
    return None


def fetch_weather(
    city: str = "아산",
    user_lat: float | None = None,
    user_lng: float | None = None,
) -> dict:
    """
    기상청 단기예보 API 호출
    반환: scoring.py에서 사용할 형식
    API 실패 시 에어코리아만 반영한 폴백 값(weather_fallback=True).

    user_lat/user_lng가 있으면 가장 가까운 충남 시군 앵커의 격자를 사용합니다.

    WEATHER_FETCH_URL 이 설정되면(예: Node 게이트웨이) 해당 호스트의 /__weather_raw__ 를 우선 사용합니다.
    """
    bridge = os.getenv("WEATHER_FETCH_URL", "").strip()
    if bridge:
        bridged = _fetch_weather_via_bridge(bridge, city, user_lat, user_lng)
        if bridged is not None:
            return bridged

    grid_city, anchor_reason = _resolve_forecast_anchor_city(city, user_lat, user_lng)
    air_city = grid_city if anchor_reason == "gps_nearest" else ((city or "").strip() if (city or "").strip() not in ("", "전체") else grid_city)

    if not settings.weather_api_key:
        out = _fallback_weather(air_city, "WEATHER_API_KEY가 설정되지 않았습니다.")
        out["forecast_anchor_city"] = grid_city
        out["forecast_anchor_reason"] = anchor_reason
        return out

    coords = GRID_COORDS[grid_city]
    base_date, base_time = get_base_time()
    now_hour = datetime.now().hour

    params = {
        "serviceKey": settings.weather_api_key,
        "numOfRows":  100,
        "pageNo":     1,
        "dataType":   "JSON",
        "base_date":  base_date,
        "base_time":  base_time,
        "nx":         coords["nx"],
        "ny":         coords["ny"],
    }

    try:
        response = request_get(
            settings.weather_forecast_url,
            params=params,
            timeout=10,
            verify=settings.requests_ssl_verify,
        )
        response.raise_for_status()
        data = response.json()
        body = data.get("response", {}).get("body", {})
        raw_items = body.get("items")
        if raw_items is None:
            items = []
        elif isinstance(raw_items, dict):
            it = raw_items.get("item")
            items = it if isinstance(it, list) else ([it] if it else [])
        else:
            items = raw_items

        header = data.get("response", {}).get("header", {})
        rc = str(header.get("resultCode", "00")).strip()
        if rc not in ("00", "0"):
            fb = _fallback_weather(
                air_city,
                f"기상청 API 오류: {header.get('resultMsg', header)}",
            )
            fb["forecast_anchor_city"] = grid_city
            fb["forecast_anchor_reason"] = anchor_reason
            return fb

        forecast, fcst_slot = _forecast_from_items(items, now_hour)

        def _num(cat: str, default: float) -> float:
            raw = forecast.get(cat)
            if raw in (None, ""):
                return default
            try:
                return float(raw)
            except (TypeError, ValueError):
                return default

        out: dict = {
            "temp":        _num("TMP", 20.0),
            "precip_prob": _num("POP", 0.0),
            "sky":         int(_num("SKY", 1.0)),
            "hour":        now_hour,
            "city":        air_city,
            "base_date":   base_date,
            "base_time":   base_time,
            "fcst_time_slot": fcst_slot,
            "dust":        1,
            "pm25":        None,
            "pm10":        None,
            "air_source":  None,
            "weather_fallback": False,
            "weather_source": "vilagefcst",
            "forecast_anchor_city": grid_city,
            "forecast_anchor_reason": anchor_reason,
        }
        return _apply_air_quality(out, air_city)
    except Exception as e:
        fb = _fallback_weather(air_city, f"{type(e).__name__}: {e}")
        fb["forecast_anchor_city"] = grid_city
        fb["forecast_anchor_reason"] = anchor_reason
        return fb


if __name__ == "__main__":
    import io, sys
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

    print("기상청 API 테스트")
    result = fetch_weather("아산")
    print(result)
