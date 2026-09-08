# -*- coding: utf-8 -*-
"""
충남 날씨 기반 관광지 추천 서비스
실행: uvicorn main:app --reload
"""
import sys
import os
import asyncio
import traceback
sys.path.insert(0, ".")

from fastapi import FastAPI, Query, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from lib.weather import fetch_weather
from lib.recommend import match_from_api
from lib.places import fetch_next_places, fetch_place_reviews

app = FastAPI(title="충남 날씨 관광 추천")

FRONTEND_DIST = os.path.join(os.path.dirname(__file__), "frontend", "dist")
STATIC_DIR    = os.path.join(os.path.dirname(__file__), "static")

if os.path.isdir(FRONTEND_DIST):
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIST, "assets")), name="assets")


# ── API 라우트 (캐치올보다 반드시 먼저) ──────────────────────────────

@app.get("/api/recommend")
async def recommend(
    city: str = Query(default="아산"),
    top_n: int = Query(default=6),
    user_lat: float = Query(default=None),
    user_lng: float = Query(default=None),
):
    try:
        loop = asyncio.get_event_loop()

        weather = await loop.run_in_executor(
            None, fetch_weather, city if city != "전체" else "아산"
        )
        result = await loop.run_in_executor(
            None,
            lambda: match_from_api(weather, city, top_n=top_n,
                                   user_lat=user_lat, user_lng=user_lng)
        )

        sky_map  = {1: "맑음", 3: "구름많음", 4: "흐림"}
        sky_text = sky_map.get(int(weather.get("sky", 1)), "알수없음")

        return {
            "city": city,
            "weather": {
                "temp":        weather["temp"],
                "precip_prob": weather["precip_prob"],
                "sky":         weather["sky"],
                "sky_text":    sky_text,
                "dust":        weather["dust"],
            },
            "scores":          result["weather"],
            "total_fetched":   result["total_fetched"],
            "recommendations": result["recommendations"],
        }

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/place-reviews")
async def place_reviews(
    name: str = Query(...),
    lat: float = Query(...),
    lng: float = Query(...),
    address: str = Query(default=""),
):
    """메인 추천 장소의 Google 리뷰 조회"""
    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, lambda: fetch_place_reviews(name, lat, lng, address)
        )
        return result
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/course")
async def course(
    lat: float = Query(...),
    lng: float = Query(...),
    category: str = Query(default="outdoor"),
    hour: int = Query(default=12),
):
    """선택한 장소 근처 다음 코스(식당/카페) 추천"""
    try:
        loop = asyncio.get_event_loop()
        places = await loop.run_in_executor(
            None,
            lambda: fetch_next_places(lat, lng, category, hour)
        )
        return {"next_places": places}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ── 프론트엔드 서빙 (항상 마지막에) ─────────────────────────────────

def _index():
    if os.path.isdir(FRONTEND_DIST):
        return FileResponse(os.path.join(FRONTEND_DIST, "index.html"))
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))

@app.get("/")
async def root():
    return _index()

@app.get("/{full_path:path}")
async def spa_fallback(full_path: str):
    return _index()
