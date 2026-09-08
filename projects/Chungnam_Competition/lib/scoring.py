from datetime import datetime


def calc_temp_score(temp: float) -> float:
    """기온을 0~1 점수로 변환 (18~24도가 최적)"""
    if 18 <= temp <= 24:
        return 1.0
    elif (12 <= temp < 18) or (24 < temp <= 28):
        return 0.7
    elif (5 <= temp < 12) or (28 < temp <= 33):
        return 0.4
    else:
        return 0.1


def calc_weather_score(weather: dict) -> dict:
    """
    날씨 데이터를 받아 각 활동 지수를 계산

    weather 파라미터:
        temp        : 기온 (°C)
        precip_prob : 강수 확률 (0~100)
        sky         : 하늘 상태 (1=맑음, 3=구름많음, 4=흐림)
        dust        : 미세먼지 (1=좋음, 2=보통, 3=나쁨, 4=매우나쁨)
        hour        : 현재 시각 (0~23)
    """
    temp        = weather.get("temp", 20)
    precip_prob = weather.get("precip_prob", 0)
    sky         = weather.get("sky", 1)
    dust        = weather.get("dust", 1)
    hour        = weather.get("hour", datetime.now().hour)

    # 개별 점수 — precip_score: 야외 활동에 “덜 불리한” 정도(높을수록 맑음에 가까움)
    temp_score = calc_temp_score(temp)
    pp = float(precip_prob)
    if pp <= 30:
        precip_score = 1.0
    elif pp <= 50:
        precip_score = 1.0 - (pp - 30) / 20 * 0.45  # 30→1.0, 50→0.55
    elif pp <= 60:
        precip_score = 0.55 - (pp - 50) / 10 * 0.33  # 50→0.55, 60→0.22
    elif pp <= 85:
        precip_score = 0.22 - (pp - 60) / 25 * 0.17  # 60→0.22, 85→0.05
    else:
        precip_score = max(0.0, 0.05 - (pp - 85) / 15 * 0.05)
    sky_score  = 1.0 if sky == 1 else 0.6 if sky == 3 else 0.3
    dust_score = 1.0 if dust == 1 else 0.7 if dust == 2 else 0.3 if dust == 3 else 0.0

    # 골든아워 (일출 6~8시, 일몰 17~19시)
    is_golden_hour = (6 <= hour <= 8) or (17 <= hour <= 19)

    # 종합 지수
    outdoor_score = (temp_score * 0.4) + (precip_score * 0.4) + (dust_score * 0.2)
    photo_score   = (sky_score * 0.6) + (0.4 if is_golden_hour else 0.0)
    indoor_score  = ((1 - precip_score) * 0.5) + ((1 - dust_score) * 0.3) + ((1 - temp_score) * 0.2)

    return {
        "outdoor": round(outdoor_score, 3),
        "photo":   round(min(photo_score, 1.0), 3),
        "indoor":  round(indoor_score, 3),
        # 60% 이상: 야외 하드필터·코스 구성 모두 “우천 대비” 구간으로 본다
        "is_raining":     pp >= 60,
        "is_dust_bad":    dust >= 3,
        "is_golden_hour": is_golden_hour,
    }
