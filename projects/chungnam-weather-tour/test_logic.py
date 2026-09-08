# -*- coding: utf-8 -*-
"""
매칭 로직 테스트 스크립트
터미널에서: python test_logic.py
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, ".")

from lib.matching import match_destinations


def print_result(label: str, weather: dict):
    print(f"\n{'='*50}")
    print(f"[시나리오] {label}")
    print(f"  날씨 입력: {weather}")
    print(f"{'='*50}")

    result = match_destinations(weather)
    scores = result["scores"]

    print(f"\n날씨 지수:")
    print(f"  야외 지수  : {scores['outdoor']}")
    print(f"  사진 지수  : {scores['photo']}")
    print(f"  실내 지수  : {scores['indoor']}")
    print(f"  비 여부    : {scores['is_raining']}")
    print(f"  미세먼지   : {'나쁨' if scores['is_dust_bad'] else '양호'}")
    print(f"  골든아워   : {scores['is_golden_hour']}")

    print(f"\n추천 관광지 TOP {len(result['recommendations'])}:")
    for i, dest in enumerate(result["recommendations"], 1):
        print(f"  {i}. [{dest['score']:.2f}] {dest['name']} ({dest['city']}) - {dest['copy']}")


# 시나리오 1: 맑고 따뜻한 오후
print_result("맑고 따뜻한 오후 (최적 야외)", {
    "temp": 22,
    "precip_prob": 10,
    "sky": 1,
    "dust": 1,
    "hour": 15
})

# 시나리오 2: 비 오는 날
print_result("비 오는 날", {
    "temp": 18,
    "precip_prob": 80,
    "sky": 4,
    "dust": 2,
    "hour": 14
})

# 시나리오 3: 골든아워 (노을)
print_result("맑은 날 골든아워 (일몰)", {
    "temp": 20,
    "precip_prob": 5,
    "sky": 1,
    "dust": 1,
    "hour": 18
})

# 시나리오 4: 미세먼지 나쁨
print_result("미세먼지 나쁨", {
    "temp": 23,
    "precip_prob": 0,
    "sky": 3,
    "dust": 3,
    "hour": 13
})
