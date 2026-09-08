# -*- coding: utf-8 -*-
"""
실시간 날씨 기반 관광지 추천 테스트
터미널에서: python -X utf8 test_realtime.py
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, ".")

from lib.weather import fetch_weather
from lib.matching import match_destinations

city = "아산"

print(f"=== {city} 실시간 날씨 기반 추천 ===\n")

# 1. 실시간 날씨 받기
weather = fetch_weather(city)
print(f"현재 날씨:")
print(f"  기온       : {weather['temp']}도")
print(f"  강수확률   : {weather['precip_prob']}%")
print(f"  하늘상태   : {'맑음' if weather['sky']==1 else '구름많음' if weather['sky']==3 else '흐림'}")
print(f"  기준시각   : {weather['base_date']} {weather['base_time']}")

# 2. 매칭
result = match_destinations(weather)
scores = result["scores"]

print(f"\n날씨 지수:")
print(f"  야외 적합도 : {scores['outdoor']}")
print(f"  사진 적합도 : {scores['photo']}")
print(f"  실내 적합도 : {scores['indoor']}")

print(f"\n오늘의 추천 장소:")
for i, dest in enumerate(result["recommendations"], 1):
    print(f"  {i}. {dest['name']} [{dest['score']:.2f}점]")
    print(f"     {dest['copy']}")
