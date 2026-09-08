# -*- coding: utf-8 -*-
"""
한국관광공사 TourAPI 4.0 연동
docs: https://api.visitkorea.or.kr
"""
import sys
from pathlib import Path

# `python lib/tourism.py` 직접 실행 시에도 프로젝트 루트가 path에 오도록 함
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from lib.config import request_get, settings

# 충남 지역코드
AREA_CODE = 34  # 충청남도
SIGUNGU_CODES = {
    "공주": 1,
    "금산": 2,
    "논산": 3,
    "당진": 4,
    "보령": 5,
    "부여": 6,
    "서산": 7,
    "서천": 8,
    "아산": 9,
    "예산": 11,
    "천안": 12,
    "청양": 13,
    "태안": 14,
    "홍성": 15,
}

CONTENT_TYPE = {
    "관광지": 12,
    "문화시설": 14,
    "축제/행사": 15,
    "여행코스": 25,
    "레포츠": 28,
    "숙박": 32,
    "쇼핑": 38,
    "음식점": 39,
}


def fetch_attractions(city: str = "아산", content_type: str = "관광지", num: int = 10) -> list:
    """
    관광공사 API로 관광지 목록 조회
    """
    sigungu = SIGUNGU_CODES.get(city)
    if sigungu is None:
        raise ValueError(f"지원하지 않는 도시: {city}")

    if not settings.tour_api_key:
        return []

    params = {
        "serviceKey":    settings.tour_api_key,
        "numOfRows":     num,
        "pageNo":        1,
        "MobileOS":      "ETC",
        "MobileApp":     "ChungnamTour",
        "_type":         "json",
        "areaCode":      AREA_CODE,
        "sigunguCode":   sigungu,
        "contentTypeId": CONTENT_TYPE.get(content_type, 12),
        "arrange":       "A",  # 제목순
    }

    url = f"{settings.tour_base_url}/areaBasedList2"
    response = request_get(url, params=params, timeout=settings.tour_api_timeout_seconds, verify=settings.requests_ssl_verify)
    response.raise_for_status()
    data = response.json()

    if data["response"]["header"]["resultCode"] != "0000":
        return []

    items = data["response"]["body"]["items"]
    if not items:
        return []

    results = []
    for item in items["item"]:
        results.append({
            "id":      item.get("contentid"),
            "name":    item.get("title"),
            "address": item.get("addr1"),
            "image":   item.get("firstimage"),
            "coords": {
                "lat": float(item.get("mapy", 0)),
                "lng": float(item.get("mapx", 0)),
            }
        })
    return results


def fetch_detail(content_id: str) -> dict:
    """관광지 상세 정보 조회"""
    if not settings.tour_api_key:
        raise ValueError("TOUR_API_KEY가 설정되지 않았습니다.")

    params = {
        "serviceKey": settings.tour_api_key,
        "MobileOS":   "ETC",
        "MobileApp":  "ChungnamTour",
        "_type":      "json",
        "contentId":  content_id,
        "defaultYN":  "Y",
        "firstImageYN": "Y",
        "addrinfoYN": "Y",
        "mapinfoYN":  "Y",
    }

    url = f"{settings.tour_base_url}/detailCommon1"
    response = request_get(url, params=params, timeout=settings.tour_api_timeout_seconds, verify=settings.requests_ssl_verify)
    response.raise_for_status()
    data = response.json()

    item = data["response"]["body"]["items"]["item"][0]
    return {
        "id":       item.get("contentid"),
        "name":     item.get("title"),
        "overview": item.get("overview"),
        "address":  item.get("addr1"),
        "image":    item.get("firstimage"),
        "homepage": item.get("homepage"),
    }


if __name__ == "__main__":
    import io, sys
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

    print("관광공사 API 테스트 - 아산 관광지")
    places = fetch_attractions("아산", "관광지", 5)
    for p in places:
        print(f"  - {p['name']} / {p['address']}")
