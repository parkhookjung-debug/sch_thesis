# -*- coding: utf-8 -*-
"""
Tour Pass catalog name matching smoke tests.
터미널: python -X utf8 test_tourpass_catalog.py
"""
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, ".")

from lib.tourpass_catalog import catalog_row_for_place


def assert_tourpass(name: str) -> None:
    row = catalog_row_for_place(name)
    assert row.get("tourpass_available") is True, (name, row)
    print(
        f"OK {name} -> {row.get('tourpass_catalog_name')} "
        f"({row.get('tourpass_match_type')})"
    )


assert_tourpass("서산버드랜드")
assert_tourpass("서산 버드랜드 카페체험")
assert_tourpass("삽교호 함상공원")

missing = catalog_row_for_place("완전히 없는 장소")
assert missing.get("tourpass_available") is None, missing
print("OK unknown place remains unmatched")
