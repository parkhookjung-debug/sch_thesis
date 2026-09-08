"""
사이트 HTML 구조 진단용 스크립트
실제 어떤 태그/클래스가 있는지 확인
"""

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time

def init_driver():
    options = Options()
    # 진단용은 headless 끄기 (사람처럼 보이게)
    options.add_argument("--window-size=1920,1080")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36")
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

driver = init_driver()

try:
    # ── 복지로 진단 ──────────────────────────────
    url = "https://www.bokjiro.go.kr/ssis-tbu/twataa/wlfareInfo/moveWlfareInfoMainList.do"
    print(f"\n접속 중: {url}")
    driver.get(url)
    time.sleep(4)

    print(f"\n[페이지 타이틀] {driver.title}")
    print(f"[현재 URL] {driver.current_url}")

    # 전체 텍스트 일부 출력 (어떤 내용이 로딩됐는지 확인)
    body_text = driver.find_element(By.TAG_NAME, "body").text
    print(f"\n[body 텍스트 앞 500자]\n{body_text[:500]}")

    # li 태그 몇 개 있는지
    li_items = driver.find_elements(By.TAG_NAME, "li")
    print(f"\n[li 태그 총 개수] {len(li_items)}")

    # 흔한 목록 컨테이너 클래스 탐색
    for selector in [".card_list", ".list_wrap", ".welfare_list", ".result_list",
                     ".contents_list", ".board_list", "ul.list", ".service_list"]:
        els = driver.find_elements(By.CSS_SELECTOR, selector)
        if els:
            print(f"  발견: {selector} ({len(els)}개)")

    # 실제 목록처럼 보이는 li 샘플 출력
    print(f"\n[li 태그 샘플 (처음 3개)]")
    for li in li_items[:3]:
        txt = li.text.strip()
        if txt:
            print(f"  ---\n  {txt[:200]}")

    # 페이지 소스 일부 저장 (선택자 분석용)
    source = driver.page_source
    with open("bokjiro_source.html", "w", encoding="utf-8") as f:
        f.write(source)
    print("\n[bokjiro_source.html 저장됨] — VS Code에서 열어서 구조 확인 가능")

finally:
    input("\n진단 완료. 엔터 누르면 브라우저 닫힘...")
    driver.quit()
