# -*- coding: utf-8 -*-
"""
한국관광공사 스토리텔링 DB 등 CSV 로컬 로더.
파일 없음·깨짐 시 빈 목록(앱은 계속 동작).
"""
from __future__ import annotations

import csv
import io
import re
from pathlib import Path
from typing import Any

from lib.config import settings

_CACHE: list[dict[str, Any]] | None = None
_CACHE_PATH: str | None = None

# 정규 필드 → 가능한 헤더 별칭(소문자 비교)
_HEADER_ALIASES: dict[str, tuple[str, ...]] = {
    # 한국관광공사 스토리텔링 DB(구 포맷): 스팟아이디, 스팟명, 오디오명, 대본내용, 재생시간(초)
    "source_id": ("source_id", "id", "story_id", "관광지id", "관광지_id", "콘텐츠id", "스팟아이디"),
    "title": ("title", "제목", "story_title", "ttl", "오디오명"),
    "city": ("city", "시도", "지역", "area", "sigungu", "시군구"),
    "district": ("district", "구군", "읍면동", "region"),
    "place_name": ("place_name", "장소명", "관광지명", "poi_name", "spot_name", "명칭", "스팟명"),
    "story_text": ("story_text", "본문", "내용", "description", "스토리", "narrative", "대본내용"),
    "summary_text": ("summary_text", "요약", "summary", "한줄", "개요"),
    "atmosphere_tags": ("atmosphere_tags", "분위기", "atmosphere", "무드"),
    "theme_tags": ("theme_tags", "테마", "theme", "키워드"),
    "lat": ("lat", "latitude", "y", "mapy", "위도"),
    "lng": ("lng", "lon", "longitude", "x", "mapx", "경도"),
}


def _norm_header(s: str) -> str:
    return re.sub(r"\s+", "", str(s).strip().lower())


def _build_header_map(fieldnames: list[str]) -> dict[str, str]:
    """canonical_key -> 실제 CSV 컬럼명."""
    inv: dict[str, str] = {}
    lowered = {_norm_header(f): f for f in fieldnames}
    for canon, aliases in _HEADER_ALIASES.items():
        for a in aliases:
            k = _norm_header(a)
            if k in lowered:
                inv[canon] = lowered[k]
                break
    return inv


def _cell(row: dict[str, str], hmap: dict[str, str], key: str) -> str:
    col = hmap.get(key)
    if not col:
        return ""
    return str(row.get(col) or "").strip()


def _split_tags(s: str) -> list[str]:
    if not s:
        return []
    parts = re.split(r"[,;|/]", s)
    return [p.strip() for p in parts if p.strip()][:24]


def _summary_from_story(story: str, max_chars: int = 160) -> str:
    story = (story or "").strip()
    if not story:
        return ""
    paras = [p.strip() for p in re.split(r"\n\s*\n", story) if p.strip()]
    first = paras[0] if paras else story
    first_line = first.split("\n", 1)[0].strip()
    if len(first_line) > max_chars:
        return first_line[: max_chars - 1].rstrip() + "…"
    return first_line


def _parse_row(row: dict[str, str], hmap: dict[str, str]) -> dict[str, Any]:
    story = _cell(row, hmap, "story_text")
    summ = _cell(row, hmap, "summary_text") or _summary_from_story(story)
    raw_row = dict(row)
    lat_s, lng_s = _cell(row, hmap, "lat"), _cell(row, hmap, "lng")
    lat_v: float | None = None
    lng_v: float | None = None
    try:
        if lat_s:
            lat_v = float(lat_s.replace(",", "."))
        if lng_s:
            lng_v = float(lng_s.replace(",", "."))
    except ValueError:
        lat_v, lng_v = None, None

    return {
        "source_id": _cell(row, hmap, "source_id") or _cell(row, hmap, "title"),
        "title": _cell(row, hmap, "title"),
        "city": _cell(row, hmap, "city"),
        "district": _cell(row, hmap, "district"),
        "place_name": _cell(row, hmap, "place_name") or _cell(row, hmap, "title"),
        "story_text": story,
        "summary_text": summ,
        "atmosphere_tags": _split_tags(_cell(row, hmap, "atmosphere_tags")),
        "theme_tags": _split_tags(_cell(row, hmap, "theme_tags")),
        "lat": lat_v,
        "lng": lng_v,
        "raw_row": raw_row,
    }


def _read_csv_text(path: Path) -> str | None:
    raw = path.read_bytes()
    # 공사 구 CSV는 CP949/EUC-KR인 경우가 많다.
    for enc in ("utf-8-sig", "utf-8", "cp949", "euc-kr"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return None


def load_storytelling_records(force_reload: bool = False) -> list[dict[str, Any]]:
    """인메모리 캐시. 경로는 settings.storytelling_csv_path."""
    global _CACHE, _CACHE_PATH
    path_str = settings.storytelling_csv_path
    if not path_str:
        return []
    path = Path(path_str)
    if not path.is_file():
        return []
    if (
        not force_reload
        and _CACHE is not None
        and _CACHE_PATH == str(path.resolve())
    ):
        return _CACHE

    text = _read_csv_text(path)
    if text is None:
        _CACHE, _CACHE_PATH = [], str(path.resolve())
        return _CACHE

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        _CACHE, _CACHE_PATH = [], str(path.resolve())
        return _CACHE

    hmap = _build_header_map(list(reader.fieldnames))
    out: list[dict[str, Any]] = []
    for row in reader:
        if not any(str(v).strip() for v in row.values() if v is not None):
            continue
        rec = _parse_row({k: (v or "") for k, v in row.items()}, hmap)
        if rec.get("place_name") or rec.get("title"):
            out.append(rec)

    _CACHE = out
    _CACHE_PATH = str(path.resolve())
    return out
