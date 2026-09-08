# -*- coding: utf-8 -*-
"""
기상청 + 관광공사 + 자동태깅 + 매칭 전체 파이프라인 테스트
터미널: python -X utf8 test_pipeline.py
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, ".")

from lib.weather import fetch_weather
from lib.recommend import match_from_api

city = "아산"

print(f"{'='*55}")
print(f"  충남 날씨 기반 관광지 추천 — {city}")
print(f"{'='*55}\n")

# 1. 실시간 날씨
weather = fetch_weather(city)
print(f"현재 날씨 ({city})")
print(f"  기온      : {weather['temp']}도")
print(f"  강수확률  : {weather['precip_prob']}%")
sky_map = {1: "맑음", 3: "구름많음", 4: "흐림"}
print(f"  하늘      : {sky_map.get(weather['sky'], '알수없음')}")
print(f"  기준시각  : {weather['base_date']} {weather['base_time']}\n")

# 2. TourAPI + 자동태깅 + 매칭
print("TourAPI 데이터 로딩 중...", flush=True)
result = match_from_api(weather, city, top_n=7)

scores = result["weather"]
print(f"\n날씨 지수")
print(f"  야외 적합도 : {scores['outdoor']}")
print(f"  사진 적합도 : {scores['photo']}")
print(f"  실내 적합도 : {scores['indoor']}")
print(f"  골든아워    : {'예' if scores['is_golden_hour'] else '아니오'}")
print(f"\n총 {result['total_fetched']}곳 분석 → 상위 {len(result['recommendations'])}곳 추천\n")

uc = result["user_coords"]
print(f"기준 위치: ({uc['lat']}, {uc['lng']})\n")
print(f"{'─'*55}")
for i, dest in enumerate(result["recommendations"], 1):
    tags = " ".join([f"#{t}" for t in dest["tags"][:3]])
    km_str = f"{dest['distance_km']}km" if dest["distance_km"] >= 0 else "거리미상"
    print(f"{i}. [{dest['score']:.2f}] {dest['name']}")
    print(f"     날씨:{dest['weather_score']:.2f} | 거리:{dest['distance_score']:.2f} ({km_str})")
    print(f"     {dest['address'][:35]}")
    print(f"     {tags}")
    print()
