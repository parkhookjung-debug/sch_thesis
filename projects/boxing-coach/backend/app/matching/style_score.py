"""
사용자 DNA vs 4명 코치 DNA — 종합 유사도 점수.

설계:
- 자세(pose) 거리:  17개 메트릭에 대해 (user - coach_avg) / coach_std 를 계산한
  z-score 의 RMS. std=0 인 메트릭은 글로벌 std 평균으로 대체.
- 펀치(punch) 거리: 펀치 타입별 6개 메트릭의 z-score RMS 를 가중 평균
  (가중치 = min(user_count, coach_count) — 충분한 표본이 있는 펀치를 더 신뢰).
- 거리 → 점수: similarity = 1 / (1 + distance), 0~1 범위.
- 종합 점수 = POSE_WEIGHT * pose_similarity + PUNCH_WEIGHT * punch_similarity.
- 4명 코치 점수를 softmax 정규화해서 confidence 도 함께 제공.
"""
from __future__ import annotations

import math
from pathlib import Path

from ..config import COACHES, COACH_DISPLAY, DATA_DIR
from ..pose.dna import DNA_METRICS, load_dna_csv
from ..pose.punch_dna import PUNCH_METRICS, PUNCH_TYPES, load_punch_dna_csv

POSE_WEIGHT = 0.6
PUNCH_WEIGHT = 0.4

# 메트릭 스케일이 매우 다르므로 std 가 0/너무 작을 때 사용할 기본 분산 (정규화 좌표 기준)
EPS_STD = 1e-3
KNEE_FALLBACK_STD = 15.0  # 무릎 각도(°) 단위
ELBOW_ANGLE_FALLBACK_STD = 20.0


def _safe_std(value: float, key: str) -> float:
    if value > EPS_STD:
        return value
    if "knee" in key:
        return KNEE_FALLBACK_STD
    if "elbow_angle" in key:
        return ELBOW_ANGLE_FALLBACK_STD
    return 0.1  # 정규화 좌표 기준 너그러운 기본값


def pose_distance(user_dna: dict, coach_dna: dict) -> float:
    """z-score 의 RMS — 단위: '평균적인 표준편차 몇 개 만큼 떨어졌나'."""
    sq_sum = 0.0
    n = 0
    for key in DNA_METRICS:
        user_val  = user_dna.get(key, 0.0)
        coach_avg = coach_dna.get(key, 0.0)
        coach_std = _safe_std(coach_dna.get(f"{key}_std", 0.0), key)
        z = (user_val - coach_avg) / coach_std
        sq_sum += z * z
        n += 1
    return math.sqrt(sq_sum / max(n, 1))


def punch_distance(
    user_punch: dict[str, dict] | None,
    coach_punch: dict[str, dict],
) -> tuple[float, dict]:
    """펀치 타입별 z-RMS 거리의 가중 평균. user_punch=None 이면 무한대 처리."""
    if not user_punch:
        return float("inf"), {"per_type": {}, "weighted": True}

    per_type = {}
    weighted_sum = 0.0
    weight_total = 0.0
    for pt in PUNCH_TYPES:
        u = user_punch.get(pt)
        c = coach_punch.get(pt)
        if u is None or c is None:
            continue
        u_count = u.get("count", 0)
        c_count = c.get("count", 0)
        if u_count < 1 or c_count < 1:
            continue
        sq = 0.0
        n = 0
        for m in PUNCH_METRICS:
            uv = u.get(f"{m}_avg", 0.0)
            cv = c.get(f"{m}_avg", 0.0)
            cs = _safe_std(c.get(f"{m}_std", 0.0), m)
            z = (uv - cv) / cs
            sq += z * z
            n += 1
        d = math.sqrt(sq / max(n, 1))
        w = min(u_count, c_count)
        per_type[pt] = {"distance": d, "weight": w}
        weighted_sum += d * w
        weight_total += w

    if weight_total == 0:
        return float("inf"), {"per_type": per_type, "weighted": False}
    return weighted_sum / weight_total, {"per_type": per_type, "weighted": True}


def _similarity(d: float) -> float:
    if math.isinf(d):
        return 0.0
    return 1.0 / (1.0 + d)


def _softmax(scores: list[float], temp: float = 1.0) -> list[float]:
    if not scores:
        return []
    m = max(scores)
    exps = [math.exp((s - m) / temp) for s in scores]
    z = sum(exps)
    return [e / z for e in exps]


def coach_dna_paths(coach: str, data_dir: Path = DATA_DIR) -> tuple[Path, Path]:
    return data_dir / f"{coach}_DNA.csv", data_dir / f"{coach}_punch_DNA.csv"


def score_user_against_all(
    user_dna: dict,
    user_punch: dict[str, dict] | None,
    data_dir: Path = DATA_DIR,
) -> dict:
    """Return per-coach scores + recommended coach."""
    per_coach = []
    for coach in COACHES:
        dna_path, punch_path = coach_dna_paths(coach, data_dir)
        if not dna_path.exists():
            print(f"[match] missing coach DNA: {dna_path.name} — skipping {coach}")
            continue
        coach_dna = load_dna_csv(dna_path)
        coach_punch = load_punch_dna_csv(punch_path) if punch_path.exists() else {}

        pose_d = pose_distance(user_dna, coach_dna)
        punch_d, punch_info = punch_distance(user_punch, coach_punch)

        pose_sim = _similarity(pose_d)
        # 펀치 표본이 부족할 때는 자세 점수만 사용
        if math.isinf(punch_d):
            combined = pose_sim
            punch_sim = 0.0
            used_punch = False
        else:
            punch_sim = _similarity(punch_d)
            combined = POSE_WEIGHT * pose_sim + PUNCH_WEIGHT * punch_sim
            used_punch = True

        per_coach.append({
            "coach": coach,
            "display": COACH_DISPLAY[coach],
            "pose_distance":  round(pose_d, 4),
            "pose_similarity": round(pose_sim, 4),
            "punch_distance": None if math.isinf(punch_d) else round(punch_d, 4),
            "punch_similarity": round(punch_sim, 4),
            "punch_breakdown": punch_info,
            "used_punch": used_punch,
            "score": round(combined, 4),
        })

    # 정규화된 확신도 (softmax)
    raw_scores = [c["score"] for c in per_coach]
    probs = _softmax(raw_scores, temp=0.15)
    for c, p in zip(per_coach, probs):
        c["confidence"] = round(p, 4)

    per_coach.sort(key=lambda x: x["score"], reverse=True)
    return {
        "recommended": per_coach[0]["coach"] if per_coach else None,
        "coaches": per_coach,
    }
