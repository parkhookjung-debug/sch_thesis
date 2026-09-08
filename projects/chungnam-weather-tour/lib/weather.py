# -*- coding: utf-8 -*-
"""
기상청 단기예보 API 연동
docs: https://www.data.go.kr/data/15084084/openapi.do
"""
import os
import math
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("WEATHER_API_KEY")
BASE_URL = "http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getVilageFcst"

# 충남 주요 지역 격자 좌표 (위경도 → X/Y 격자)
GRID_COORDS = {
    "아산": {"nx": 67, "ny": 100},
    "천안": {"nx": 67, "ny": 100},
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


def fetch_weather(city: str = "아산") -> dict:
    """
    기상청 단기예보 API 호출
    반환: scoring.py에서 사용할 형식
    """
    if city not in GRID_COORDS:
        raise ValueError(f"지원하지 않는 도시: {city}. 지원 목록: {list(GRID_COORDS.keys())}")

    coords = GRID_COORDS[city]
    base_date, base_time = get_base_time()
    now_hour = datetime.now().hour

    params = {
        "serviceKey": API_KEY,
        "numOfRows":  100,
        "pageNo":     1,
        "dataType":   "JSON",
        "base_date":  base_date,
        "base_time":  base_time,
        "nx":         coords["nx"],
        "ny":         coords["ny"],
    }

    response = requests.get(BASE_URL, params=params, timeout=10)
    response.raise_for_status()
    data = response.json()

    items = data["response"]["body"]["items"]["item"]

    # 현재 시각에 해당하는 예보 파싱
    forecast = {}
    target_time = f"{now_hour:02d}00"

    for item in items:
        if item["fcstTime"] == target_time:
            forecast[item["category"]] = item["fcstValue"]

    # 필요한 값 추출 (기상청 카테고리 코드)
    return {
        "temp":        float(forecast.get("TMP", 20)),     # 기온
        "precip_prob": float(forecast.get("POP", 0)),      # 강수확률
        "sky":         int(forecast.get("SKY", 1)),        # 하늘상태
        "hour":        now_hour,
        "city":        city,
        "base_date":   base_date,
        "base_time":   base_time,
        # 미세먼지는 별도 API 필요 (기본값 1=좋음으로 설정)
        "dust":        1,
    }


if __name__ == "__main__":
    import io, sys
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

    print("기상청 API 테스트")
    result = fetch_weather("아산")
    print(result)
