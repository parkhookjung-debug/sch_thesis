"""Concatenate two event-NPZ files (e.g. MMPose-extracted + rtmlib-extracted)
into a single dataset for joint training. Each input pose source becomes
its own 'video' (suffixed) so LOVO still treats them as separate sources.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np


def load_npz(path: Path):
    d = np.load(path, allow_pickle=True)
    metas = [json.loads(s) for s in d["meta"]]
    return d["X"].astype(np.float32), d["y"].astype(np.int64), [str(c) for c in d["classes"]], metas


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", type=Path, required=True)
    ap.add_argument("--b", type=Path, required=True)
    ap.add_argument("--suffix-a", default="mm")
    ap.add_argument("--suffix-b", default="rt")
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()

    Xa, ya, ca, ma = load_npz(args.a)
    Xb, yb, cb, mb = load_npz(args.b)
    if ca != cb:
        raise SystemExit(f"class lists differ:\n  a={ca}\n  b={cb}")

    for m in ma:
        m["video_id"] = f"{m['video_id']}::{args.suffix_a}"
    for m in mb:
        m["video_id"] = f"{m['video_id']}::{args.suffix_b}"

    X = np.concatenate([Xa, Xb], axis=0)
    y = np.concatenate([ya, yb], axis=0)
    meta = ma + mb

    args.output.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        args.output,
        X=X, y=y,
        classes=np.asarray(ca),
        meta=np.asarray([json.dumps(m, ensure_ascii=True) for m in meta]),
    )
    print(f"Wrote {args.output}")
    print(f"  total samples: {len(X)}  (a={len(Xa)}, b={len(Xb)})")
    print(f"  classes: {ca}")
    print(f"  per-class: {dict(zip(ca, np.bincount(y, minlength=len(ca)).tolist()))}")


if __name__ == "__main__":
    main()
