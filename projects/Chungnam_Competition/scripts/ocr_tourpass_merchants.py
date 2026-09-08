#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HTML 텍스트 + 상세 이미지 OCR 병합 → raw.txt / CSV
실행: python scripts/ocr_tourpass_merchants.py (크롤러에서 호출)

의존성: pip install -r requirements-ocr.txt  (EasyOCR)
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path

SOURCE_URL_DEFAULT = "https://smartstore.naver.com/lscompany01/products/10218084169"

CITIES = (
    "천안",
    "공주",
    "보령",
    "아산",
    "서산",
    "논산",
    "계룡",
    "당진",
    "금산",
    "부여",
    "서천",
    "청양",
    "홍성",
    "예산",
    "태안",
)

NOISE_PATTERNS = re.compile(
    r"^(□|■|●|○|◆|◇|\d{1,3}\s*$|범례|할인율|무료입장|문의|고객센터|배송|교환|반품|"
    r"네이버|스마트스토어|장바구니|구매하기|상품정보|리뷰|Q&A|판매자|쿠폰)",
    re.I,
)

MERCHANT_KEYWORDS = re.compile(
    r"가맹점|투어패스|충남|충청남도|이용안내|혜택|상세\s*정보"
)


def read_text_file(p: Path) -> str:
    if not p.exists():
        return ""
    return p.read_text(encoding="utf-8", errors="replace")


def normalize_line(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())


def line_looks_like_noise(line: str) -> bool:
    t = normalize_line(line)
    if len(t) < 2:
        return True
    if NOISE_PATTERNS.search(t):
        return True
    if re.fullmatch(r"[\d\s\-\.\:]+", t):
        return True
    if MERCHANT_KEYWORDS.fullmatch(t):
        return True
    if "©" in t or "NAVER" in t.upper() or "openstreetmap" in t.lower():
        return True
    return False


def is_city_header(line: str) -> str | None:
    t = normalize_line(line)
    for c in CITIES:
        if t == c or t.startswith(c + " ") or t.startswith(c + "시") or t.startswith(c + "군"):
            return c
        if t.startswith(c + "·"):
            return c
    return None


def guess_category(name: str) -> str:
    rules = (
        (("카페", "커피", "베이커리", "디저트"), "카페"),
        (("식당", "한우", "국밥", "갈비", "횟집", "맛집", "음식", "고기", "한정식"), "음식점"),
        (
            ("박물관", "미술관", "전시", "생태원", "수목원", "공원", "사적", "문화재", "전망"),
            "관광지",
        ),
        (("체험", "공방", "농장", "승마", "레저", "카트", "레일"), "체험"),
        (("호텔", "펜션", "리조트", "숙박", "모텔"), "숙박"),
    )
    for keys, lab in rules:
        if any(k in name for k in keys):
            return lab
    return "확인필요"


def guess_benefit(line: str) -> str:
    t = normalize_line(line)
    if "무료" in t and "입장" in t:
        return "무료입장"
    if "할인" in t:
        return "할인"
    if "음료" in t or "제공" in t:
        return "음료제공"
    return "확인필요"


def ocr_images_easyocr(image_paths: list[Path]) -> list[tuple[str, str]]:
    try:
        import easyocr  # type: ignore
    except ImportError:
        print(
            "오류: EasyOCR 미설치입니다. 다음을 실행하세요:\n"
            "  pip install -r requirements-ocr.txt",
            file=sys.stderr,
        )
        return []

    reader = easyocr.Reader(["ko", "en"], gpu=False, verbose=False)
    out: list[tuple[str, str]] = []
    for p in sorted(image_paths):
        try:
            lines = reader.readtext(str(p), detail=0, paragraph=False)
            text = "\n".join(str(x) for x in lines if x)
            out.append((p.name, text))
        except Exception as e:  # noqa: BLE001
            print(f"OCR 실패 ({p.name}): {e}", file=sys.stderr)
            out.append((p.name, ""))
    return out


def parse_merchants_from_blocks(
    raw_lines: list[str],
    *,
    source: str,
    source_image: str,
    base_confidence: float,
) -> list[dict]:
    rows: list[dict] = []
    current_city = ""
    for raw in raw_lines:
        line = normalize_line(raw)
        if not line:
            continue
        ch = is_city_header(line)
        if ch:
            current_city = ch
            continue
        if line_looks_like_noise(line):
            continue
        city = current_city
        name = line
        benefit_type = guess_benefit(line)
        cat = guess_category(name)
        conf = base_confidence
        needs = conf < 0.72 or not city
        if re.search(r"[◇◆�]", name) or len(name) > 60:
            needs = True
            conf = min(conf, 0.45)
        rows.append(
            {
                "city": city,
                "merchant_name": name,
                "category": cat,
                "benefit_type": benefit_type,
                "address": "",
                "phone": "",
                "source_url": source,
                "source_image": source_image,
                "raw_text": line,
                "confidence": round(conf, 3),
                "needs_review": needs,
            }
        )
    return rows


def dedupe_preserve_order(items: list[dict]) -> list[dict]:
    seen: set[tuple[str, str]] = set()
    out: list[dict] = []
    for it in items:
        key = (it["city"], it["merchant_name"])
        if key in seen:
            continue
        seen.add(key)
        out.append(it)
    return out


def write_csv_bom(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "city",
        "merchant_name",
        "category",
        "benefit_type",
        "address",
        "phone",
        "source_url",
        "source_image",
        "raw_text",
        "confidence",
        "needs_review",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            out = dict(r)
            out["needs_review"] = "true" if out.get("needs_review") else "false"
            w.writerow(out)


def html_text_may_contain_merchant_list(text: str) -> bool:
    if any(c in text for c in CITIES) and (
        "가맹" in text or "투어패스" in text or "혜택" in text
    ):
        return True
    return False


def _is_blocked_page_text(text: str) -> bool:
    t = (text or "").strip()
    if not t:
        return True
    markers = (
        "현재 서비스 접속이 불가",
        "접속이 불가합니다",
        "서비스 접속이 불가",
        "Too Many Requests",
    )
    return any(m in t for m in markers)


def _configure_stdio() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
            sys.stderr.reconfigure(encoding="utf-8")
        except Exception:
            pass


def main() -> int:
    _configure_stdio()
    ap = argparse.ArgumentParser()
    ap.add_argument("--html-text", required=True)
    ap.add_argument("--image-manifest", required=True)
    ap.add_argument("--images-dir", required=True)
    ap.add_argument("--out-raw", required=True)
    ap.add_argument("--out-csv", required=True)
    ap.add_argument("--source-url", default=SOURCE_URL_DEFAULT)
    args = ap.parse_args()

    html_path = Path(args.html_text)
    manifest_path = Path(args.image_manifest)
    images_dir = Path(args.images_dir)
    out_raw = Path(args.out_raw)
    out_csv = Path(args.out_csv)
    source_url = args.source_url

    html_body = read_text_file(html_path)
    blocked = html_body.startswith("[[BLOCKED_OR_ERROR]]")
    if blocked:
        html_body = html_body.replace("[[BLOCKED_OR_ERROR]]\n", "", 1)
    if not blocked and _is_blocked_page_text(html_body):
        blocked = True

    manifest_items: list[dict] = []
    if manifest_path.exists():
        try:
            manifest_items = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            print(f"이미지 매니페스트 JSON 파싱 실패: {e}", file=sys.stderr)

    image_files = [images_dir / m["filename"] for m in manifest_items if m.get("filename")]
    image_files = [p for p in image_files if p.is_file()]

    raw_sections: list[str] = []
    raw_sections.append("===== HTML / innerText =====\n")
    raw_sections.append(html_body)

    ocr_results: list[tuple[str, str]] = []
    if image_files:
        ocr_results = ocr_images_easyocr(image_files)
        for fn, txt in ocr_results:
            raw_sections.append(f"\n===== OCR: {fn} =====\n")
            raw_sections.append(txt)

    full_raw = "\n".join(raw_sections)
    out_raw.parent.mkdir(parents=True, exist_ok=True)
    try:
        out_raw.write_text(full_raw, encoding="utf-8")
    except OSError as e:
        print(f"RAW 저장 실패: {e}", file=sys.stderr)
        return 1

    all_rows: list[dict] = []

    html_lines = html_body.replace("\r\n", "\n").split("\n")
    if html_text_may_contain_merchant_list(html_body) and not blocked:
        all_rows.extend(
            parse_merchants_from_blocks(
                html_lines,
                source=source_url,
                source_image="",
                base_confidence=0.78,
            )
        )

    for fn, txt in ocr_results:
        lines = txt.replace("\r\n", "\n").split("\n")
        all_rows.extend(
            parse_merchants_from_blocks(
                lines,
                source=source_url,
                source_image=fn,
                base_confidence=0.52,
            )
        )

    if not all_rows and ocr_results:
        for fn, txt in ocr_results:
            lines = txt.replace("\r\n", "\n").split("\n")
            all_rows.extend(
                parse_merchants_from_blocks(
                    lines,
                    source=source_url,
                    source_image=fn,
                    base_confidence=0.48,
                )
            )

    all_rows = dedupe_preserve_order(all_rows)

    if not all_rows:
        msg = (
            "[차단·오류로 상세 본문 미수신 — 브라우저에서 URL을 직접 연 뒤 재실행]"
            if blocked
            else "[가맹점 파싱 실패 — 원문 검수]"
        )
        all_rows.append(
            {
                "city": "",
                "merchant_name": msg,
                "category": "확인필요",
                "benefit_type": "확인필요",
                "address": "",
                "phone": "",
                "source_url": source_url,
                "source_image": "",
                "raw_text": (full_raw[:2000] + ("…" if len(full_raw) > 2000 else "")),
                "confidence": 0.05 if blocked else 0.1,
                "needs_review": True,
            }
        )

    try:
        write_csv_bom(out_csv, all_rows)
    except OSError as e:
        print(f"CSV 저장 실패: {e}", file=sys.stderr)
        return 1

    raw_line_count = len([ln for ln in full_raw.splitlines() if ln.strip()])
    review_n = sum(1 for r in all_rows if r.get("needs_review") is True)
    by_city = Counter((r["city"] or "(미분류)") for r in all_rows)

    print("\n========== 검증 ==========")
    print(f"다운로드·매니페스트 이미지: {len(manifest_items)}개")
    print(f"OCR 처리한 이미지: {len(ocr_results)}개")
    print(f"추출된 raw text 줄 수(공백 제외): {raw_line_count}")
    print(f"CSV 행 개수: {len(all_rows)}")
    print("city별 가맹점 개수:")
    for k in sorted(by_city.keys(), key=lambda x: (-by_city[x], x)):
        print(f"  {k}: {by_city[k]}")
    print(f"needs_review=true: {review_n}개")
    print(f"CSV 저장: {out_csv.resolve()}")
    print(f"RAW 저장: {out_raw.resolve()}")
    print("==========================\n")

    if not ocr_results and not html_text_may_contain_merchant_list(html_body):
        print(
            "경고: HTML에서 가맹점 목록 키워드를 찾기 어렵고 OCR 이미지도 없습니다.",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
