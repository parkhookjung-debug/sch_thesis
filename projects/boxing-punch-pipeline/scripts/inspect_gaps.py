"""Inspect frame gaps between labeled punches per video."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
labels = pd.read_csv(ROOT / "data" / "labels" / "labels.csv", comment="#")

for csv_path in sorted((ROOT / "data" / "raw").glob("*.pose.csv")):
    df = pd.read_csv(csv_path, usecols=["video_id", "frame_index"])
    vid = str(df["video_id"].iloc[0])
    first, last = int(df["frame_index"].min()), int(df["frame_index"].max())
    v = labels[labels["video_id"] == vid].sort_values("start_frame")
    print(f"\n{vid}  video frames [{first}..{last}]  labels={len(v)}")
    if v.empty:
        continue
    prev_end = first
    for row in v.itertuples(index=False):
        gap = int(row.start_frame) - prev_end
        marker = "  <-- GAP" if gap >= 20 else ""
        print(f"  gap={gap:4d}  punch[{int(row.start_frame):4d}..{int(row.end_frame):4d}]={row.label}{marker}")
        prev_end = int(row.end_frame)
    tail_gap = last - prev_end
    marker = "  <-- TAIL GAP" if tail_gap >= 20 else ""
    print(f"  tail gap={tail_gap}{marker}")
