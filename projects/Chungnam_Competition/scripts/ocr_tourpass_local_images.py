#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
로컬 PNG에서만 OCR → 콘솔/텍스트 파일로 raw 출력 (CSV 파싱은 별도).
  pip install easyocr opencv-python-headless
  python scripts/ocr_tourpass_local_images.py output/images/tourpass_map_01.png ...
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("images", nargs="+", help="이미지 경로들")
    ap.add_argument("--out", "-o", help="raw 텍스트 저장 경로")
    args = ap.parse_args()

    try:
        import easyocr  # type: ignore
    except ImportError:
        print("easyocr 미설치: pip install easyocr opencv-python-headless", file=sys.stderr)
        return 1

    reader = easyocr.Reader(["ko", "en"], gpu=False, verbose=False)
    chunks: list[str] = []
    for p in args.images:
        path = Path(p)
        if not path.is_file():
            print(f"없음: {path}", file=sys.stderr)
            continue
        lines = reader.readtext(str(path), detail=0, paragraph=True)
        text = "\n".join(str(x) for x in lines if x)
        chunks.append(f"===== {path.name} =====\n{text}")

    out = "\n\n".join(chunks)
    if args.out:
        Path(args.out).write_text(out, encoding="utf-8")
        print("저장:", args.out)
    else:
        print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
