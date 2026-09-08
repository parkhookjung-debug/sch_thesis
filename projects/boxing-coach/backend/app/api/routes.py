"""FastAPI 라우트."""
from __future__ import annotations

import shutil
import traceback
from dataclasses import asdict
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse

from ..config import COACH_DISPLAY, COACHES, DATA_DIR, RESULTS_DIR, UPLOADS_DIR
from ..coaching.session import analyze_user_video, render_coaching_video
from ..matching.style_score import coach_dna_paths, score_user_against_all
from ..pose.dna import load_dna_csv
from .jobs import create_job, get_job, progress_updater, update_job

router = APIRouter()


# ─────────────────────────────────────────────────────────────────
# 코치 메타데이터
# ─────────────────────────────────────────────────────────────────
@router.get("/coaches")
def list_coaches():
    out = []
    for c in COACHES:
        dna_path, punch_path = coach_dna_paths(c)
        out.append({
            "id": c,
            **COACH_DISPLAY[c],
            "ready": dna_path.exists(),
            "punch_dna_ready": punch_path.exists(),
        })
    return {"coaches": out}


# ─────────────────────────────────────────────────────────────────
# 스타일 분석 — 사용자 영상 → 4명 점수
# ─────────────────────────────────────────────────────────────────
def _save_upload(upload: UploadFile, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("wb") as f:
        shutil.copyfileobj(upload.file, f)


def _run_analyze_style(job_id: str, video_path: Path):
    try:
        update_job(job_id, status="running", progress_label="포즈 추출 중")
        work_dir = UPLOADS_DIR / job_id
        analysis = analyze_user_video(
            video_path, work_dir,
            progress=progress_updater(job_id, "포즈 추출 중"),
        )
        update_job(job_id, progress=0.9, progress_label="스타일 매칭 중")
        scoring = score_user_against_all(
            analysis["user_dna"], analysis["user_punch"], DATA_DIR,
        )
        result = {
            **scoring,
            "frames_used": analysis["frames_used"],
            "user_punch_counts": {k: int(v.get("count", 0)) for k, v in analysis["user_punch"].items()},
        }
        update_job(job_id, status="done", progress=1.0, progress_label="완료", result=result)
    except Exception as e:
        update_job(job_id, status="failed",
                   error=f"{type(e).__name__}: {e}\n{traceback.format_exc()[-1500:]}")


@router.post("/analyze-style")
def analyze_style(background: BackgroundTasks, video: UploadFile = File(...)):
    if not video.filename:
        raise HTTPException(400, "filename missing")
    job = create_job(kind="analyze-style")
    dest = UPLOADS_DIR / f"{job.id}_{video.filename}"
    _save_upload(video, dest)
    background.add_task(_run_analyze_style, job.id, dest)
    return {"job_id": job.id}


# ─────────────────────────────────────────────────────────────────
# 코칭 세션 — 영상 + 코치 선택 → 결과 영상
# ─────────────────────────────────────────────────────────────────
def _run_coaching_session(job_id: str, video_path: Path, coach: str):
    try:
        update_job(job_id, status="running", progress_label="분석 중")
        dna_path, _ = coach_dna_paths(coach)
        if not dna_path.exists():
            raise FileNotFoundError(f"코치 DNA 가 없습니다: {dna_path}. "
                                    f"먼저 데이터 재생성 스크립트를 실행하세요.")
        coach_dna = load_dna_csv(dna_path)
        coach_label = COACH_DISPLAY[coach]["name"]
        out_video = RESULTS_DIR / f"{job_id}_coaching.mp4"
        summary = render_coaching_video(
            video_path, out_video, coach_dna, coach_label,
            progress=progress_updater(job_id, "코칭 영상 합성 중"),
        )
        summary["video_url"] = f"/api/result/{job_id}_coaching.mp4"
        summary["coach"] = {"id": coach, **COACH_DISPLAY[coach]}
        update_job(job_id, status="done", progress=1.0, progress_label="완료", result=summary)
    except Exception as e:
        update_job(job_id, status="failed",
                   error=f"{type(e).__name__}: {e}\n{traceback.format_exc()[-1500:]}")


@router.post("/coaching-session")
def coaching_session(
    background: BackgroundTasks,
    coach: str = Form(...),
    video: UploadFile = File(...),
):
    if coach not in COACHES:
        raise HTTPException(400, f"unknown coach: {coach}")
    if not video.filename:
        raise HTTPException(400, "filename missing")
    job = create_job(kind="coaching-session")
    dest = UPLOADS_DIR / f"{job.id}_{video.filename}"
    _save_upload(video, dest)
    background.add_task(_run_coaching_session, job.id, dest, coach)
    return {"job_id": job.id, "coach": coach}


# ─────────────────────────────────────────────────────────────────
# Job 상태 / 결과 파일
# ─────────────────────────────────────────────────────────────────
@router.get("/jobs/{job_id}")
def job_status(job_id: str):
    job = get_job(job_id)
    if job is None:
        raise HTTPException(404, "job not found")
    return {
        "id": job.id,
        "kind": job.kind,
        "status": job.status,
        "progress": job.progress,
        "progress_label": job.progress_label,
        "error": job.error,
        "result": job.result,
    }


@router.get("/result/{filename}")
def result_file(filename: str):
    """결과 영상 다운로드/스트리밍 (mp4)."""
    # path traversal 방지
    fname = Path(filename).name
    target = RESULTS_DIR / fname
    if not target.exists():
        raise HTTPException(404, "file not found")
    return FileResponse(target, media_type="video/mp4")
