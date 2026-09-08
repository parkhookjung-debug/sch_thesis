import json
from pathlib import Path
from lib.scoring import calc_weather_score


DESTINATIONS_PATH = Path(__file__).parent.parent / "data" / "destinations.json"


def load_destinations() -> list:
    with open(DESTINATIONS_PATH, encoding="utf-8") as f:
        return json.load(f)


def match_destinations(weather: dict, top_n: int = 5) -> dict:
    """
    날씨 데이터를 기반으로 관광지를 매칭하여 상위 N개 반환

    반환:
        {
            "scores": 날씨 지수,
            "recommendations": 정렬된 관광지 리스트
        }
    """
    scores = calc_weather_score(weather)
    destinations = load_destinations()

    results = []
    for dest in destinations:
        w = dest["weather_weights"]

        # Hard Filter: 비 오는 날 야외 장소 제외
        if scores["is_raining"] and dest["category"] == "outdoor":
            continue

        # Hard Filter: 미세먼지 나쁨 + 장소가 미세먼지 민감한 경우 제외
        if scores["is_dust_bad"] and w.get("fine_dust_limit") == "good":
            continue

        # Soft Scoring
        if dest["category"] == "outdoor":
            base_score = scores["outdoor"] * w["sunny"]
        else:
            base_score = scores["indoor"] * w["rainy"]

        # 골든아워 보너스
        golden_bonus = 0.3 if (dest.get("golden_hour_bonus") and scores["is_golden_hour"]) else 0.0

        total = min(base_score + golden_bonus, 1.0)

        results.append({
            **dest,
            "score": round(total, 3)
        })

    results.sort(key=lambda x: x["score"], reverse=True)

    return {
        "scores": scores,
        "recommendations": results[:top_n]
    }
