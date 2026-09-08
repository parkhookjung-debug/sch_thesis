"""
복지 정보 크롤러 - 쇼츠 콘텐츠용
수집 대상: 복지로, 정부24
목적: 지원금/혜택 정보 수집 → 쇼츠 스크립트 재료
"""

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import pandas as pd
import time
import json
from datetime import datetime

# ─────────────────────────────────────────
# 브라우저 초기화
# ─────────────────────────────────────────
def init_driver(headless=True):
    options = Options()
    if headless:
        options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)


# ─────────────────────────────────────────
# 1. 복지로 크롤링
#    URL: https://www.bokjiro.go.kr
#    수집: 복지서비스 목록 (제목, 지원대상, 지원내용, 신청방법)
# ─────────────────────────────────────────
def crawl_bokjiro(driver, max_pages=3):
    results = []
    base_url = "https://www.bokjiro.go.kr/ssis-tbu/twataa/wlfareInfo/moveWlfareInfoMainList.do"

    for page in range(1, max_pages + 1):
        print(f"  복지로 {page}페이지 수집 중...")
        driver.get(f"{base_url}?curPage={page}&srchKeyCode=01&tabId=01")
        time.sleep(2)

        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".card_list li"))
            )
        except:
            print(f"  {page}페이지 로딩 실패, 건너뜀")
            continue

        items = driver.find_elements(By.CSS_SELECTOR, ".card_list li")
        for item in items:
            try:
                title = item.find_element(By.CSS_SELECTOR, ".tit").text.strip()
                summary = item.find_element(By.CSS_SELECTOR, ".txt").text.strip()
                tags_el = item.find_elements(By.CSS_SELECTOR, ".tag_list span")
                tags = [t.text.strip() for t in tags_el]

                # 지원금/혜택 관련 키워드 필터
                if is_useful_content(title, summary):
                    results.append({
                        "출처": "복지로",
                        "제목": title,
                        "요약": summary,
                        "태그": ", ".join(tags),
                        "수집일": datetime.today().strftime("%Y-%m-%d"),
                    })
            except:
                continue

    return results


# ─────────────────────────────────────────
# 2. 정부24 크롤링
#    URL: https://www.gov.kr
#    수집: 생활정보 서비스 목록
# ─────────────────────────────────────────
def crawl_gov24(driver, max_pages=3):
    results = []
    base_url = "https://www.gov.kr/portal/service/serviceList"

    for page in range(1, max_pages + 1):
        print(f"  정부24 {page}페이지 수집 중...")
        driver.get(f"{base_url}?pagerOffset={( page - 1) * 10}")
        time.sleep(2)

        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".list_service li"))
            )
        except:
            print(f"  {page}페이지 로딩 실패, 건너뜀")
            continue

        items = driver.find_elements(By.CSS_SELECTOR, ".list_service li")
        for item in items:
            try:
                title = item.find_element(By.CSS_SELECTOR, ".tit_service").text.strip()
                desc = item.find_element(By.CSS_SELECTOR, ".desc").text.strip()

                if is_useful_content(title, desc):
                    results.append({
                        "출처": "정부24",
                        "제목": title,
                        "요약": desc,
                        "태그": "",
                        "수집일": datetime.today().strftime("%Y-%m-%d"),
                    })
            except:
                continue

    return results


# ─────────────────────────────────────────
# 필터: 쇼츠에 쓸만한 정보인지 판단
# 키워드 점수 기반 — 높을수록 유용한 콘텐츠
# ─────────────────────────────────────────
USEFUL_KEYWORDS = [
    "지원금", "지원", "혜택", "바우처", "보조금", "장려금", "수당",
    "무료", "할인", "환급", "감면", "청년", "노인", "육아", "출산",
    "취업", "창업", "임산부", "저소득", "긴급", "의료비", "주거",
]

def is_useful_content(title, summary, threshold=1):
    text = title + summary
    score = sum(1 for kw in USEFUL_KEYWORDS if kw in text)
    return score >= threshold


# ─────────────────────────────────────────
# 메인 실행
# ─────────────────────────────────────────
def main():
    print("=== 복지 정보 크롤링 시작 ===")
    driver = init_driver(headless=True)

    all_results = []

    try:
        print("\n[1/2] 복지로 수집")
        all_results += crawl_bokjiro(driver, max_pages=3)

        print("\n[2/2] 정부24 수집")
        all_results += crawl_gov24(driver, max_pages=3)

    finally:
        driver.quit()

    # 중복 제거 (제목 기준)
    seen = set()
    unique = []
    for item in all_results:
        if item["제목"] not in seen:
            seen.add(item["제목"])
            unique.append(item)

    print(f"\n총 {len(unique)}건 수집 완료")

    # CSV 저장
    df = pd.DataFrame(unique)
    df.to_csv("welfare_data.csv", index=False, encoding="utf-8-sig")
    print("welfare_data.csv 저장 완료")

    # JSON 저장 (쇼츠 생성 파이프라인용)
    with open("welfare_data.json", "w", encoding="utf-8") as f:
        json.dump(unique, f, ensure_ascii=False, indent=2)
    print("welfare_data.json 저장 완료")

    # 미리보기
    print("\n─── 수집 데이터 미리보기 (상위 5건) ───")
    for i, item in enumerate(unique[:5], 1):
        print(f"\n[{i}] {item['출처']} | {item['제목']}")
        print(f"    {item['요약'][:60]}...")


if __name__ == "__main__":
    main()
