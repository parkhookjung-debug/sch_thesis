from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from preprocessing import build_dataset


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-dir", required=True, type=Path)
    parser.add_argument("--labels", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--window-size", type=int, default=64)
    parser.add_argument("--stride", type=int, default=8)
    parser.add_argument("--min-overlap", type=float, default=0.25)
    parser.add_argument("--none-stride", type=int, default=0, help="Extra stride for sampling clean none windows. 0 disables.")
    parser.add_argument("--max-none-ratio", type=float, default=1.0)
    args = parser.parse_args()

    build_dataset(
        raw_dir=args.raw_dir,
        labels_path=args.labels,
        output_path=args.output,
        window_size=args.window_size,
        stride=args.stride,
        min_overlap=args.min_overlap,
        none_stride=args.none_stride or None,
        max_none_ratio=args.max_none_ratio,
    )
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
