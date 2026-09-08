"""
실시간 코칭 WebSocket.

프로토콜
────────
Client → Server (JSON 텍스트)
  { "type": "frame", "frame_id": 123, "image": "data:image/jpeg;base64,..." }
  { "type": "reset" }                              # 카운터 초기화
  { "type": "toggle_facing" }                      # 우향/좌향 전환 (lead/rear)
  { "type": "set_view", "mode": "front"|"side"|"auto" }  # view 모드 강제/해제

Server → Client (JSON 텍스트)
  { "type": "ready", "coach": {...}, "available_views": ["side","front"] }
  { "type": "frame_result",
    "frame_id": ..., "kp": [[x,y],...17], "sc": [...17],
    "width": int, "height": int,
    "facing_right": bool,
    "view_mode": "front"|"side"|"ambiguous",
    "view_locked": bool,
    "punch_events": [...],
    "counts": {"jab":N, "cross":N, "hook":N, "uppercut":N},
    "posture": {"total":85, "grade":"A", "items":[...]} | None,
    "warnings": [str]      # 예: "전신이 화면에 들어오지 않음"
  }
"""
from __future__ import annotations

import asyncio
import base64
import json
import time
import traceback

import cv2
import numpy as np
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..config import COACH_DISPLAY, COACHES, DATA_DIR, VIS_MIN
from ..coaching.keypoints import (
    KP_L_AN, KP_L_HI, KP_L_KN, KP_R_AN, KP_R_HI, KP_R_KN,
    detect_facing,
)
from ..coaching.posture import calc_posture
from ..coaching.posture_front import calc_posture_front
from ..coaching.punch_detector import PunchDetectorState, feed as feed_punch
from ..coaching.view_runtime import ViewDetector
from ..pose.dna import load_dna_csv
from ..pose.dna_front import load_dna_front_csv
from ..pose.extractor import get_model

router = APIRouter()


def _decode_jpeg_dataurl(data: str) -> np.ndarray | None:
    if "," in data:
        data = data.split(",", 1)[1]
    try:
        raw = base64.b64decode(data, validate=False)
    except Exception:
        return None
    arr = np.frombuffer(raw, dtype=np.uint8)
    return cv2.imdecode(arr, cv2.IMREAD_COLOR)


def _check_full_body(kp: np.ndarray, sc: np.ndarray, h: int) -> list[str]:
    """전신 시인성 경고 메시지 목록."""
    warnings: list[str] = []
    lower = (KP_L_HI, KP_R_HI, KP_L_KN, KP_R_KN, KP_L_AN, KP_R_AN)
    if all(sc[i] < 0.3 for i in lower):
        warnings.append("하체가 화면에 안 보입니다 (스탠스 평가 보류)")
    elif any(kp[i][1] > h - 5 for i in (KP_L_AN, KP_R_AN) if sc[i] > 0.3):
        warnings.append("발이 화면 하단에 잘림")
    return warnings


@router.websocket("/ws/realtime/{coach_id}")
async def realtime_coaching(ws: WebSocket, coach_id: str):
    await ws.accept()

    if coach_id not in COACHES:
        await ws.send_json({"type": "error", "message": f"unknown coach: {coach_id}"})
        await ws.close()
        return

    side_path  = DATA_DIR / f"{coach_id}_DNA.csv"
    front_path = DATA_DIR / f"{coach_id}_DNA_front.csv"
    coach_dna_side  = load_dna_csv(side_path) if side_path.exists() else None
    coach_dna_front = load_dna_front_csv(front_path) if front_path.exists() else None

    if coach_dna_side is None and coach_dna_front is None:
        await ws.send_json({
            "type": "error",
            "message": f"코치 DNA 가 없습니다. scripts/build_dna.py 를 먼저 실행하세요.",
        })
        await ws.close()
        return

    available_views = []
    if coach_dna_side  is not None: available_views.append("side")
    if coach_dna_front is not None: available_views.append("front")

    state = PunchDetectorState(facing_right=True)
    view = ViewDetector(window=30)
    facing_locked = False

    loop = asyncio.get_event_loop()
    model = await loop.run_in_executor(None, get_model)

    await ws.send_json({
        "type": "ready",
        "coach": {"id": coach_id, **COACH_DISPLAY[coach_id]},
        "available_views": available_views,
    })

    pending: dict[str, object] | None = None
    pending_lock = asyncio.Lock()
    closed = False

    async def reader():
        nonlocal pending, closed, facing_locked
        try:
            while True:
                msg = await ws.receive_text()
                try:
                    payload = json.loads(msg)
                except Exception:
                    continue
                mtype = payload.get("type")
                if mtype == "frame":
                    async with pending_lock:
                        pending = payload
                elif mtype == "reset":
                    for k in state.counts:
                        state.counts[k] = 0
                elif mtype == "toggle_facing":
                    state.facing_right = not state.facing_right
                    facing_locked = True
                elif mtype == "set_view":
                    mode = payload.get("mode")
                    if mode == "auto":
                        view._locked = False
                        view._ratios.clear()
                        view._mode = "ambiguous"
                    elif mode in ("front", "side"):
                        view.force(mode)
        except WebSocketDisconnect:
            pass
        except Exception:
            traceback.print_exc()
        finally:
            closed = True

    async def worker():
        nonlocal pending, facing_locked
        frame_counter = 0
        try:
            while not closed:
                async with pending_lock:
                    job = pending
                    pending = None
                if job is None:
                    await asyncio.sleep(0.015)
                    continue

                frame_id = job.get("frame_id")
                img = _decode_jpeg_dataurl(job.get("image") or "")
                if img is None:
                    continue
                fh, fw = img.shape[:2]
                rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                kps, scs = await loop.run_in_executor(None, lambda: model(rgb))
                frame_counter += 1
                now = time.time()

                kp_list: list = []
                sc_list: list = []
                events_serialized: list[dict] = []
                posture_serialized: dict | None = None
                warnings: list[str] = []
                view_mode = view.mode

                if len(kps) > 0:
                    kp = kps[0]
                    sc = scs[0]

                    if not facing_locked and frame_counter <= 30:
                        state.facing_right = detect_facing(kp, sc)
                        if frame_counter == 30:
                            facing_locked = True

                    view_mode = view.update(kp, sc)

                    events = feed_punch(state, kp, sc, frame_counter, now)
                    for ev in events:
                        events_serialized.append({
                            "type": str(ev.punch_type), "side": str(ev.side),
                            "arm_extension": float(ev.arm_extension),
                            "elbow_angle": float(ev.elbow_angle),
                            "lean_forward": float(ev.lean_forward),
                        })

                    # 모드에 맞는 DNA + 점수 함수 선택
                    if view_mode == "front" and coach_dna_front is not None:
                        p = calc_posture_front(kp, sc, coach_dna_front)
                    elif view_mode == "side" and coach_dna_side is not None:
                        p = calc_posture(kp, sc, coach_dna_side, facing_right=state.facing_right)
                    else:
                        # ambiguous — 사용 가능한 첫번째 DNA로 fallback (대개 측면)
                        if coach_dna_side is not None:
                            p = calc_posture(kp, sc, coach_dna_side, facing_right=state.facing_right)
                        elif coach_dna_front is not None:
                            p = calc_posture_front(kp, sc, coach_dna_front)
                        else:
                            p = None

                    if p is not None:
                        posture_serialized = {
                            "total": int(p.total),
                            "grade": str(p.grade),
                            "items": [
                                {"label": it.label, "score": int(it.score),
                                 "max": int(it.max_score), "message": it.message}
                                for it in p.items
                            ],
                        }
                    warnings = _check_full_body(kp, sc, fh)
                    # visibility 0.5 이상만 클라이언트에 그리기 위해 변환
                    kp_list = [[float(x), float(y)] for x, y in kp]
                    sc_list = [float(s) for s in sc]

                await ws.send_json({
                    "type": "frame_result",
                    "frame_id": frame_id,
                    "width": int(fw),
                    "height": int(fh),
                    "kp": kp_list,
                    "sc": sc_list,
                    "facing_right": bool(state.facing_right),
                    "view_mode": str(view_mode),
                    "view_locked": bool(view.locked),
                    "punch_events": events_serialized,
                    "counts": {k: int(v) for k, v in state.counts.items()},
                    "posture": posture_serialized,
                    "warnings": warnings,
                })
        except WebSocketDisconnect:
            pass
        except Exception as e:
            try:
                await ws.send_json({"type": "error", "message": f"{type(e).__name__}: {e}"})
            except Exception:
                pass
            traceback.print_exc()

    await asyncio.gather(reader(), worker())

    try:
        await ws.close()
    except Exception:
        pass
