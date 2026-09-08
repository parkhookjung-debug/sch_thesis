"""FastAPI 엔트리포인트.

실행:
  cd backend
  uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.realtime import router as realtime_router
from .api.routes import router

app = FastAPI(title="복싱 코치 API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")
app.include_router(realtime_router, prefix="/api")


@app.get("/")
def root():
    return {"name": "복싱 코치 API", "docs": "/docs"}
