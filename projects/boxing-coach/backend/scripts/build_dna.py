"""
backend/data/full_data/*_full_data*.csv  →
  backend/data/{coach}_DNA.csv          (측면 자세 DNA)
  backend/data/{coach}_DNA_front.csv    (정면 자세 DNA)
  backend/data/{coach}_punch_DNA.csv    (펀치 DNA — 측면 영상 기준)

사용법
  python -m scripts.build_dna             # 4명 전체
  python -m scripts.build_dna bivol lim   # 일부만

영상별로 정면/측면을 자동 분류해서, 측면 영상은 측면 DNA 로, 정면 영상은
정면 DNA 로 들어간다. ambiguous 영상은 양쪽 모두에 넣어 표본 수를 확보.

펀치 DNA 는 측면 메트릭(어깨폭 X²+Z²)에 의존하므로 측면 + ambiguous 만 사용.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Windows cp949 콘솔에서도 한글/유니코드 출력
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import DATA_DIR
from app.pose.dna import aggregate_dna_from_csvs, save_dna_csv
from app.pose.dna_front import aggregate_dna_front, save_dna_front_csv
from app.pose.punch_dna import aggregate_punch_dna, save_punch_dna_csv
from app.pose.view_classifier import classify_csv

FULL_DIR = DATA_DIR / "full_data"

# 사용자 수동 라벨 — 자동 분류기보다 우선 적용.
# 자동 분류기가 ratio/ear_diff 기반이라 사선 자세 영상을 잘못 분류할 수 있어,
# 사용자가 보유한 영상에 대해 직접 'front' / 'side' 를 박아 두는 매니페스트.
# (없는 파일은 자동 분류기 결과를 그대로 사용)
MANUAL_VIEWS: dict[str, str] = {
    "lim_full_data1.csv": "side",
    "lim_full_data2.csv": "side",
    "lim_full_data3.csv": "front",
    "lim_full_data4.csv": "front",
    "lim_full_data5.csv": "side",
}


COACH_INPUTS = {
    "lim": [
        "lim_full_data1.csv",
        "lim_full_data2.csv",
        "lim_full_data3.csv",
        "lim_full_data4.csv",
        "lim_full_data5.csv",
    ],
    "bivol": [
        "bivol_full_data1.csv",
        "bivol_full_data2.csv",
        "bivol_full_data3.csv",
        "bivol_full_data4.csv",
    ],
    "canelo": [
        "canelo_full_data1.csv",
        "canelo_full_data2.csv",
        "canelo_full_data3.csv",
        "canelo_full_data4.csv",
        "canelo_full_data7.csv",
    ],
    "garcia": [
        "garcia_full_data1.csv",
        "garcia_full_data2.csv",
        "garcia_full_data3.csv",
        "garcia_full_data4.csv",
        "garcia_full_data5.csv",
        "garcia_full_data6.csv",
    ],
}


def _classify_files(files: list[Path]) -> dict[str, list[Path]]:
    """파일별 view 분류. 매니페스트(MANUAL_VIEWS) 가 있으면 그것을 우선."""
    out = {"front": [], "side": [], "ambiguous": []}
    for f in files:
        manual = MANUAL_VIEWS.get(f.name)
        mode, ratio, ear, n = classify_csv(f)
        rs = f"{ratio:.3f}" if ratio is not None else "n/a"
        es = f"{ear:.3f}"   if ear   is not None else "n/a"
        if manual in ("front", "side"):
            out[manual].append(f)
            print(f"  - {f.name:<32} ratio={rs:>6} ear={es:>6} n={n:>4} -> {manual} (manual)")
        else:
            out[mode].append(f)
            print(f"  - {f.name:<32} ratio={rs:>6} ear={es:>6} n={n:>4} -> {mode}")
    return out


def main(coaches: list[str]) -> int:
    if not FULL_DIR.exists():
        print(f"[FATAL] full_data 폴더 없음: {FULL_DIR}\n"
              f"        먼저 `python -m scripts.extract_videos` 를 실행하세요.")
        return 1

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    for coach in coaches:
        if coach not in COACH_INPUTS:
            print(f"[skip] 알 수 없는 코치: {coach}")
            continue
        files = [FULL_DIR / f for f in COACH_INPUTS[coach] if (FULL_DIR / f).exists()]
        if not files:
            print(f"[skip] {coach}: full_data CSV 없음")
            continue

        print(f"\n=== {coach.upper()} 분류 ===")
        buckets = _classify_files(files)

        side_set  = buckets["side"]  + buckets["ambiguous"]
        front_set = buckets["front"] + buckets["ambiguous"]
        punch_set = side_set  # 측면 메트릭 의존

        # 측면 DNA
        print(f"\n--- {coach.upper()} 측면 DNA  (입력 {len(side_set)} CSV) ---")
        if side_set:
            dna = aggregate_dna_from_csvs(side_set)
            print(f"  자세 프레임 사용: {dna['_frames_used']}/{dna['_frames_total']}")
            save_dna_csv(dna, DATA_DIR / f"{coach}_DNA.csv")
            print(f"  → 저장: {coach}_DNA.csv")
        else:
            print("  (측면/모호 영상 없음 — skip)")

        # 정면 DNA
        print(f"\n--- {coach.upper()} 정면 DNA  (입력 {len(front_set)} CSV) ---")
        if front_set:
            dnaf = aggregate_dna_front(front_set)
            print(f"  자세 프레임 사용: {dnaf['_frames_used']}/{dnaf['_frames_total']}")
            save_dna_front_csv(dnaf, DATA_DIR / f"{coach}_DNA_front.csv")
            print(f"  → 저장: {coach}_DNA_front.csv")
        else:
            print("  (정면/모호 영상 없음 — skip)")

        # 펀치 DNA (측면 기준)
        print(f"\n--- {coach.upper()} Punch DNA (입력 {len(punch_set)} CSV) ---")
        if punch_set:
            punch_rows = aggregate_punch_dna(punch_set)
            save_punch_dna_csv(punch_rows, DATA_DIR / f"{coach}_punch_DNA.csv")
            for row in punch_rows:
                print(f"  {row['punch_type']:<9} n={row['count']:>3}  "
                      f"arm_ext={row['arm_extension_avg']:.3f}  "
                      f"elbow_ang={row['elbow_angle_avg']:.1f}°")
            print(f"  → 저장: {coach}_punch_DNA.csv")
        else:
            print("  (측면 영상 없음 — punch DNA skip)")
    return 0


if __name__ == "__main__":
    args = [a.lower() for a in sys.argv[1:]] or list(COACH_INPUTS.keys())
    raise SystemExit(main(args))
