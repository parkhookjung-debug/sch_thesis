from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd


def video_id_from_path(path: Path) -> str:
    match = re.search(r"LIM\s*(\d+)_labels", path.stem, flags=re.IGNORECASE)
    if not match:
        raise ValueError(f"Cannot infer LIM index from {path.name}")
    return f"LIM {int(match.group(1))}"


def convert_file(path: Path, pre_frames: int, post_frames: int) -> pd.DataFrame:
    df = pd.read_csv(path)
    required = {"frame_number", "punch_type"}
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(f"{path} missing columns: {sorted(missing)}")

    video_id = video_id_from_path(path)
    out = pd.DataFrame(
        {
            "video_id": video_id,
            "start_frame": (df["frame_number"].astype(int) - pre_frames).clip(lower=0),
            "end_frame": df["frame_number"].astype(int) + post_frames,
            "label": df["punch_type"].astype(str).str.strip().str.lower(),
            "point_frame": df["frame_number"].astype(int),
            "source_file": path.name,
        }
    )
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--pre-frames", type=int, default=12)
    parser.add_argument("--post-frames", type=int, default=12)
    args = parser.parse_args()

    files = sorted(args.input_dir.glob("LIM*_labels.csv"))
    if not files:
        raise SystemExit(f"No LIM*_labels.csv files found in {args.input_dir}")

    labels = pd.concat(
        [convert_file(path, args.pre_frames, args.post_frames) for path in files],
        ignore_index=True,
    )
    labels = labels.sort_values(["video_id", "point_frame"]).reset_index(drop=True)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    labels.to_csv(args.output, index=False)

    counts = labels.groupby(["video_id", "label"]).size().unstack(fill_value=0)
    print(f"Wrote {args.output}")
    print(counts)


if __name__ == "__main__":
    main()
