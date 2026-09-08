"""
4명 코치의 원본 영상에서 RTMPose 키포인트 시퀀스를 일괄 추출.

기존 폴더 `c:/Users/parkh/통합/VScode/복싱/` 에 있는 LIM/Bivol/Canelo/Garcia
영상을 그대로 입력으로 쓴다. 결과는 `backend/data/full_data/` 에 저장.

bivol/canelo/garcia 영상은 원본이 MediaPipe 33 키포인트로 추출돼 있어
LIM과 비교 불가능하므로, 모두 동일한 RTMPose(COCO 17) 형식으로 재추출한다.

사용법
  python -m scripts.extract_videos              # 4명 전체
  python -m scripts.extract_videos bivol canelo # 일부만
"""
from __future__ import annotations

import sys
from pathlib import Path
from time import perf_counter

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

# scripts/ 가 backend/ 의 형제 폴더라서 PYTHONPATH 보정
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import DATA_DIR
from app.pose.extractor import extract_video_to_csv

# 기존 데이터가 있는 위치
SOURCE_DIR = Path("c:/Users/parkh/통합/VScode/복싱")

# 코치별 (영상 파일명, 출력 CSV 파일명) 매핑
# LIM3.mp4는 정면 촬영이라 측면 기반 DNA에서는 제외하지만 영상 자체는 추출함
COACH_VIDEOS = {
    "lim": [
        ("LIM1.mp4", "lim_full_data1.csv"),
        ("LIM2.mp4", "lim_full_data2.csv"),
        ("LIM3.mp4", "lim_full_data3.csv"),
        ("LIM4.mp4", "lim_full_data4.csv"),
        ("LIM5.mp4", "lim_full_data5.csv"),
    ],
    "bivol": [
        ("bivol.mp4",  "bivol_full_data1.csv"),
        ("bivol2.mp4", "bivol_full_data2.csv"),
        ("bivol3.mp4", "bivol_full_data3.csv"),
        ("bivol4.mp4", "bivol_full_data4.csv"),
    ],
    "canelo": [
        ("canelo.mp4",  "canelo_full_data1.csv"),
        ("canelo2.mp4", "canelo_full_data2.csv"),
        ("canelo3.mp4", "canelo_full_data3.csv"),
        ("canelo4.mp4", "canelo_full_data4.csv"),
        ("canelo7.mp4", "canelo_full_data7.csv"),
    ],
    "garcia": [
        ("garcia.mp4",  "garcia_full_data1.csv"),
        ("garcia2.mp4", "garcia_full_data2.csv"),
        ("garcia3.mp4", "garcia_full_data3.csv"),
        ("garcia4.mp4", "garcia_full_data4.csv"),
        ("garcia5.mp4", "garcia_full_data5.csv"),
        ("garcia6.mp4", "garcia_full_data6.csv"),
    ],
}

OUT_SUBDIR = DATA_DIR / "full_data"


def _progress_printer(label):
    last = [0]

    def cb(cur, total):
        # 5% 단위로만 출력
        if total <= 0:
            return
        pct = int(cur * 100 / total)
        if pct >= last[0] + 5 or cur == total:
            last[0] = pct
            print(f"  [{label}] {pct:3d}%  ({cur}/{total})", end="\r", flush=True)

    return cb


def main(coaches: list[str]) -> int:
    OUT_SUBDIR.mkdir(parents=True, exist_ok=True)

    if not SOURCE_DIR.exists():
        print(f"[FATAL] 원본 영상 폴더가 없습니다: {SOURCE_DIR}")
        return 1

    overall_start = perf_counter()
    total_videos = 0
    skipped_videos = 0

    for coach in coaches:
        if coach not in COACH_VIDEOS:
            print(f"[skip] 알 수 없는 코치: {coach}")
            continue
        print(f"\n=== {coach.upper()} ===")
        for video_name, csv_name in COACH_VIDEOS[coach]:
            video_path = SOURCE_DIR / video_name
            csv_path = OUT_SUBDIR / csv_name
            total_videos += 1
            if not video_path.exists():
                print(f"  [skip] 영상 없음: {video_name}")
                skipped_videos += 1
                continue
            if csv_path.exists():
                print(f"  [skip] 이미 존재: {csv_name}  (삭제 후 재실행하면 다시 추출)")
                skipped_videos += 1
                continue
            print(f"  → {video_name}  →  {csv_name}")
            t0 = perf_counter()
            result = extract_video_to_csv(video_path, csv_path, progress=_progress_printer(video_name))
            dur = perf_counter() - t0
            print(f"\n     완료: 저장 {result['saved']}프레임 / 미인식 {result['skipped']}프레임 / {dur:.1f}s")

    print(f"\n전체 소요: {perf_counter() - overall_start:.1f}s "
          f"(총 {total_videos}편, 건너뜀 {skipped_videos}편)")
    return 0


if __name__ == "__main__":
    args = [a.lower() for a in sys.argv[1:]] or list(COACH_VIDEOS.keys())
    raise SystemExit(main(args))
