"""Centralized paths and constants."""
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BACKEND_DIR / "data"
UPLOADS_DIR = BACKEND_DIR / "uploads"
RESULTS_DIR = BACKEND_DIR / "results"

for d in (DATA_DIR, UPLOADS_DIR, RESULTS_DIR):
    d.mkdir(parents=True, exist_ok=True)

RTMO_URL = (
    "https://download.openmmlab.com/mmpose/v1/projects/rtmo/onnx_sdk/"
    "rtmo-s_8xb32-600e_body7-640x640-dac2bf74_20231211.zip"
)

COACHES = ["bivol", "canelo", "garcia", "lim"]

COACH_DISPLAY = {
    "bivol":  {"name": "Dmitry Bivol",      "style": "정밀 아웃복서",     "tagline": "긴 잽과 절제된 거리감"},
    "canelo": {"name": "Canelo Álvarez",    "style": "카운터 인파이터",   "tagline": "묵직한 바디샷과 더블 훅"},
    "garcia": {"name": "Ryan Garcia",       "style": "스피드 박서",       "tagline": "폭발적인 콤비네이션"},
    "lim":    {"name": "임관우 (LIM)",       "style": "사이드 무빙 카운터", "tagline": "각도 변환과 측면 컴팩트 가드"},
}

VIS_MIN = 0.30
VISIBILITY_MIN_DNA = 0.45
