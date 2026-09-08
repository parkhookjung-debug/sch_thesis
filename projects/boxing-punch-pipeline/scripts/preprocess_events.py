from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from preprocessing import build_event_dataset


def main() -> None:
    parser = argparse.ArgumentParser(description="Build event-centered ST-GCN dataset from punch labels.")
    parser.add_argument("--raw-dir", required=True, type=Path)
    parser.add_argument("--labels", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--window-size", type=int, default=32)
    parser.add_argument("--context-frames", type=int, default=4)
    parser.add_argument("--shift-radius", type=int, default=2)
    args = parser.parse_args()

    build_event_dataset(
        raw_dir=args.raw_dir,
        labels_path=args.labels,
        output_path=args.output,
        window_size=args.window_size,
        context_frames=args.context_frames,
        shift_radius=args.shift_radius,
    )
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
