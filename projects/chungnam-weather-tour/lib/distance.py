# -*- coding: utf-8 -*-
"""
거리 점수 계산 (Haversine 공식)
가까울수록 높은 점수 (0~1)
"""
import math

# 충남 주요 도시 중심 좌표 (사용자 위치 기본값)
CITY_CENTERS = {
    "아산": (36.7897, 127.0041),
    "천안": (36.8151, 127.1139),
    "공주": (36.4467, 127.1191),
    "보령": (36.3330, 126.6128),
    "서산": (36.7849, 126.4503),
    "논산": (36.1872, 127.0987),
    "부여": (36.2753, 126.9099),
    "태안": (36.7454, 126.2980),
    "당진": (36.8896, 126.6458),
    "홍성": (36.6012, 126.6607),
}

# 거리 가중치 설정 (km)
NEAR_KM   = 10   # 이 거리 이내 → 1.0점
FAR_KM    = 60   # 이 거리 이상 → 0.0점


def haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """두 좌표 간 거리 계산 (km)"""
    R = 6371
    d_lat = math.radians(lat2 - lat1)
    d_lng = math.radians(lng2 - lng1)
    a = (math.sin(d_lat / 2) ** 2
         + math.cos(math.radians(lat1))
         * math.cos(math.radians(lat2))
         * math.sin(d_lng / 2) ** 2)
    return R * 2 * math.asin(math.sqrt(a))


def calc_distance_score(dest_lat: float, dest_lng: float,
                         user_lat: float, user_lng: float) -> tuple[float, float]:
    """
    반환: (거리 점수 0~1, 실제 거리 km)
    가까울수록 점수 높음, FAR_KM 이상이면 0점
    """
    if dest_lat == 0 or dest_lng == 0:
        return 0.5, -1  # 좌표 없으면 중간값

    km = haversine(user_lat, user_lng, dest_lat, dest_lng)

    if km <= NEAR_KM:
        score = 1.0
    elif km >= FAR_KM:
        score = 0.0
    else:
        # 선형 감소
        score = 1.0 - (km - NEAR_KM) / (FAR_KM - NEAR_KM)

    return round(score, 3), round(km, 1)


def get_user_coords(city: str) -> tuple[float, float]:
    """도시 이름으로 기본 좌표 반환"""
    return CITY_CENTERS.get(city, CITY_CENTERS["아산"])
