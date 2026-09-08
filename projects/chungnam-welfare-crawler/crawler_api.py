"""
복지로 Open API 크롤러
공공데이터포털(data.go.kr)에서 API 키 발급 필요

발급 방법:
1. https://www.data.go.kr 접속 → 회원가입
2. 검색창에 "복지서비스목록정보" 검색
3. [한국사회보장정보원_복지서비스목록정보] 활용신청
4. 마이페이지 → 일반 인증키(Encoding) 복사 → 아래 API_KEY에 붙여넣기
"""

import requests
import pandas as pd
import json
from datetime import datetime

# ─────────────────────────────────────────
# ★ 여기에 발급받은 API 키 입력
# ─────────────────────────────────────────
API_KEY = "여기에_API_키_입력"

BASE_URL = "http://www.bokjiro.go.kr/openapi/rest/wlfareInfo"

# 수집할 대상 키워드 (쇼츠에 쓸 주제)
USEFUL_KEYWORDS = [
    "지원금", "지원", "혜택", "바우처", "보조금", "장려금", "수당",
    "무료", "할인", "환급", "감면", "청년", "노인", "육아", "출산",
    "취업", "창업", "임산부", "저소득", "긴급", "의료비", "주거",
]


def fetch_welfare_list(page=1, per_page=100):
    """복지로 API에서 복지서비스 목록 가져오기"""
    params = {
        "serviceKey": API_KEY,
        "callTp":     "L",        # L = 목록 조회
        "srchKeyCode": "01",      # 01 = 서비스명
        "pageIndex":  page,
        "numOfRows":  per_page,
        "inqTpCd":    "",
        "bizCd":      "",
    }

    try:
        res = requests.get(BASE_URL, params=params, timeout=10)
        res.raise_for_status()
        data = res.json()
        return data.get("wlfareInfo", {}).get("list", [])
    except Exception as e:
        print(f"  API 오류 (page {page}): {e}")
        return []


def fetch_welfare_detail(wlfareInfoId):
    """개별 복지서비스 상세 정보 가져오기"""
    params = {
        "serviceKey":  API_KEY,
        "callTp":      "D",       # D = 상세 조회
        "wlfareInfoId": wlfareInfoId,
    }

    try:
        res = requests.get(BASE_URL, params=params, timeout=10)
        res.raise_for_status()
        data = res.json()
        detail = data.get("wlfareInfo", {}).get("list", [{}])[0]
        return detail
    except:
        return {}


def is_useful(item):
    """키워드 기반 필터링"""
    text = str(item.get("wlfareSynm", "")) + str(item.get("wlfareOverview", ""))
    return any(kw in text for kw in USEFUL_KEYWORDS)


def main():
    print("=== 복지로 Open API 수집 시작 ===\n")

    all_items = []
    max_pages = 5  # 필요시 늘리기 (1페이지 = 100건)

    for page in range(1, max_pages + 1):
        print(f"[{page}/{max_pages}페이지] 수집 중...")
        items = fetch_welfare_list(page=page, per_page=100)

        if not items:
            print("  더 이상 데이터 없음.")
            break

        for item in items:
            if not is_useful(item):
                continue

            # 상세 정보 추가 수집 (선택사항 — API 호출 수 늘어남)
            # detail = fetch_welfare_detail(item.get("wlfareInfoId", ""))

            all_items.append({
                "출처":        "복지로",
                "서비스ID":    item.get("wlfareInfoId", ""),
                "제목":        item.get("wlfareSynm", "").strip(),
                "지원대상":    item.get("tgterIndvdlCd", "").strip(),
                "요약":        item.get("wlfareOverview", "").strip()[:200],
                "소관부처":    item.get("jurMnofNm", "").strip(),
                "신청방법":    item.get("aplyMthdCd", "").strip(),
                "수집일":      datetime.today().strftime("%Y-%m-%d"),
            })

        print(f"  → 누적 {len(all_items)}건 (필터 통과)")

    print(f"\n총 {len(all_items)}건 수집 완료")

    if not all_items:
        print("\n⚠ 데이터가 없습니다. API 키를 확인해주세요.")
        return

    # 저장
    df = pd.DataFrame(all_items)
    df.to_csv("welfare_data.csv", index=False, encoding="utf-8-sig")

    with open("welfare_data.json", "w", encoding="utf-8") as f:
        json.dump(all_items, f, ensure_ascii=False, indent=2)

    print("welfare_data.csv / welfare_data.json 저장 완료")

    # 미리보기
    print("\n─── 미리보기 (상위 5건) ───")
    for i, item in enumerate(all_items[:5], 1):
        print(f"\n[{i}] {item['제목']}")
        print(f"    대상: {item['지원대상']}")
        print(f"    내용: {item['요약'][:80]}...")


if __name__ == "__main__":
    main()
