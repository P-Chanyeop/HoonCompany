"""
func.py — 네이버 카페 자동화 핵심 함수 모음
SOFTCAT | SC-2026-0401-CF

※ CSS 셀렉터, 카페 URL, API 키 등 사용자 환경에 따라 달라지는 값은
  주석에 '# 수동 입력 필요' 로 표시되어 있습니다. 직접 확인 후 수정하세요.
"""

import os
import re
import time
import logging
from typing import Optional

import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import gspread
from google.oauth2.service_account import Credentials
import google.generativeai as genai

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s — %(message)s")
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════
# 1. 계정 / 프록시 로드
# ═══════════════════════════════════════════════

def load_accounts(filepath: str) -> list[dict]:
    """계정 파일(ID:PW) 로드. 한 줄에 ID:PW 형식."""
    accounts = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split(":", 1)
            if len(parts) == 2:
                accounts.append({"id": parts[0].strip(), "pw": parts[1].strip()})
    logger.info(f"계정 {len(accounts)}개 로드 완료")
    return accounts


def load_proxies(proxy_input: str) -> list[str]:
    """
    프록시 로드. 파일 경로(.txt)이면 파일에서, 아니면 단일 프록시 문자열로 처리.
    형식: IP:PORT 또는 IP:PORT:USER:PW
    """
    if os.path.isfile(proxy_input):
        proxies = []
        with open(proxy_input, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    proxies.append(line)
        logger.info(f"프록시 {len(proxies)}개 로드 완료")
        return proxies
    elif proxy_input.strip():
        return [proxy_input.strip()]
    return []


def parse_proxy(proxy_str: str) -> dict:
    """프록시 문자열을 selenium/requests 용 dict로 변환."""
    parts = proxy_str.split(":")
    if len(parts) == 4:
        ip, port, user, pw = parts
        url = f"http://{user}:{pw}@{ip}:{port}"
    elif len(parts) == 2:
        ip, port = parts
        url = f"http://{ip}:{port}"
    else:
        raise ValueError(f"프록시 형식 오류: {proxy_str}")
    return {"http": url, "https": url}


# ═══════════════════════════════════════════════
# 2. 브라우저(Selenium) 생성
# ═══════════════════════════════════════════════

def create_driver(proxy: Optional[str] = None, headless: bool = True) -> webdriver.Chrome:
    """Chrome WebDriver 생성. 프록시는 IP:PORT 또는 IP:PORT:USER:PW 형식."""
    opts = Options()
    if headless:
        opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
    if proxy:
        p = parse_proxy(proxy)
        opts.add_argument(f"--proxy-server={p['http']}")
    driver = webdriver.Chrome(options=opts)
    driver.implicitly_wait(5)
    return driver


# ═══════════════════════════════════════════════
# 3. 네이버 로그인
# ═══════════════════════════════════════════════

def naver_login(driver: webdriver.Chrome, naver_id: str, naver_pw: str) -> bool:
    """
    네이버 로그인.
    # 수동 입력 필요: 네이버 로그인 페이지 구조가 변경되면 셀렉터 수정 필요
    """
    LOGIN_URL = "https://nid.naver.com/nidlogin.login"
    # 수동 입력 필요: 로그인 폼 CSS 셀렉터 (네이버 업데이트 시 변경될 수 있음)
    ID_SELECTOR = "#id"
    PW_SELECTOR = "#pw"
    LOGIN_BTN_SELECTOR = ".btn_login"

    try:
        driver.get(LOGIN_URL)
        time.sleep(1)

        # clipboard 방식으로 입력 (자동입력 감지 우회)
        id_input = driver.find_element(By.CSS_SELECTOR, ID_SELECTOR)
        driver.execute_script(f"arguments[0].value = '{naver_id}';", id_input)

        pw_input = driver.find_element(By.CSS_SELECTOR, PW_SELECTOR)
        driver.execute_script(f"arguments[0].value = '{naver_pw}';", pw_input)

        driver.find_element(By.CSS_SELECTOR, LOGIN_BTN_SELECTOR).click()
        time.sleep(2)

        if "nid.naver.com" not in driver.current_url:
            logger.info(f"로그인 성공: {naver_id}")
            return True
        logger.warning(f"로그인 실패: {naver_id}")
        return False
    except Exception as e:
        logger.error(f"로그인 에러 ({naver_id}): {e}")
        return False


# ═══════════════════════════════════════════════
# 4. 카페 가입 / 가입 여부 확인
# ═══════════════════════════════════════════════

def check_cafe_membership(driver: webdriver.Chrome, cafe_id: str) -> bool:
    """카페 가입 여부 확인."""
    # 수동 입력 필요: 가입 여부 판별 CSS 셀렉터 (카페 구조 변경 시 수정)
    MEMBER_INDICATOR_SELECTOR = ".nick_btn"
    try:
        driver.get(f"https://cafe.naver.com/{cafe_id}")
        time.sleep(2)
        elements = driver.find_elements(By.CSS_SELECTOR, MEMBER_INDICATOR_SELECTOR)
        return len(elements) > 0
    except Exception as e:
        logger.error(f"가입 여부 확인 실패 ({cafe_id}): {e}")
        return False


def auto_join_cafe(driver: webdriver.Chrome, cafe_id: str) -> bool:
    """카페 미가입 시 자동 가입."""
    # 수동 입력 필요: 가입 버튼 / 가입 폼 CSS 셀렉터
    JOIN_BTN_SELECTOR = ".btn_join"
    CONFIRM_BTN_SELECTOR = ".btn_submit"
    try:
        driver.get(f"https://cafe.naver.com/{cafe_id}")
        time.sleep(2)
        join_btn = driver.find_elements(By.CSS_SELECTOR, JOIN_BTN_SELECTOR)
        if not join_btn:
            logger.info(f"이미 가입된 카페: {cafe_id}")
            return True
        join_btn[0].click()
        time.sleep(2)
        confirm = driver.find_elements(By.CSS_SELECTOR, CONFIRM_BTN_SELECTOR)
        if confirm:
            confirm[0].click()
            time.sleep(2)
        logger.info(f"카페 가입 완료: {cafe_id}")
        return True
    except Exception as e:
        logger.error(f"카페 가입 실패 ({cafe_id}): {e}")
        return False


# ═══════════════════════════════════════════════
# 5. 등급 확인 / 게시판 탐색
# ═══════════════════════════════════════════════

def get_member_grade(driver: webdriver.Chrome, cafe_id: str) -> str:
    """카페 내 현재 계정의 등급 조회."""
    # 수동 입력 필요: 등급 표시 CSS 셀렉터
    GRADE_SELECTOR = ".nick_level"
    try:
        driver.get(f"https://cafe.naver.com/{cafe_id}")
        time.sleep(2)
        el = driver.find_elements(By.CSS_SELECTOR, GRADE_SELECTOR)
        if el:
            grade = el[0].text.strip()
            logger.info(f"등급 확인: {grade}")
            return grade
        return "알수없음"
    except Exception as e:
        logger.error(f"등급 확인 실패: {e}")
        return "에러"


def find_writable_boards(driver: webdriver.Chrome, cafe_id: str) -> list[dict]:
    """글쓰기 가능한 게시판 목록 자동 탐색."""
    # 수동 입력 필요: 게시판 목록 CSS 셀렉터
    BOARD_LIST_SELECTOR = ".cafe-menu-list a"
    boards = []
    try:
        driver.get(f"https://cafe.naver.com/{cafe_id}")
        time.sleep(2)
        elements = driver.find_elements(By.CSS_SELECTOR, BOARD_LIST_SELECTOR)
        for el in elements:
            href = el.get_attribute("href") or ""
            match = re.search(r"menuid=(\d+)", href)
            if match:
                boards.append({"name": el.text.strip(), "menu_id": match.group(1)})
        logger.info(f"게시판 {len(boards)}개 탐색 완료")
    except Exception as e:
        logger.error(f"게시판 탐색 실패: {e}")
    return boards


# ═══════════════════════════════════════════════
# 6. 카페 글쓰기
# ═══════════════════════════════════════════════

def write_cafe_post(driver: webdriver.Chrome, cafe_id: str, menu_id: str,
                    title: str, content: str, allow_comment: bool = True) -> bool:
    """네이버 카페 글쓰기."""
    # 수동 입력 필요: 글쓰기 에디터 CSS 셀렉터 (네이버 스마트에디터 구조에 따라 변경)
    TITLE_SELECTOR = ".se-title-input"
    CONTENT_SELECTOR = ".se-text-paragraph"
    SUBMIT_BTN_SELECTOR = ".btn_submit"
    COMMENT_TOGGLE_SELECTOR = ".checkbox_comment"

    WRITE_URL = f"https://cafe.naver.com/ca-fe/cafes/{ cafe_id }/articles/write?boardType=L&menuId={menu_id}"
    try:
        driver.get(WRITE_URL)
        time.sleep(3)

        # 제목 입력
        title_el = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, TITLE_SELECTOR))
        )
        title_el.click()
        title_el.send_keys(title)

        # 본문 입력
        content_el = driver.find_element(By.CSS_SELECTOR, CONTENT_SELECTOR)
        content_el.click()
        content_el.send_keys(content)

        # 댓글 허용 토글
        if not allow_comment:
            toggle = driver.find_elements(By.CSS_SELECTOR, COMMENT_TOGGLE_SELECTOR)
            if toggle:
                toggle[0].click()

        # 등록
        driver.find_element(By.CSS_SELECTOR, SUBMIT_BTN_SELECTOR).click()
        time.sleep(3)
        logger.info(f"글쓰기 완료: {title[:20]}...")
        return True
    except Exception as e:
        logger.error(f"글쓰기 실패: {e}")
        return False


# ═══════════════════════════════════════════════
# 7. 답글(댓글) 작성
# ═══════════════════════════════════════════════

def write_comment(driver: webdriver.Chrome, article_url: str, comment_text: str) -> bool:
    """게시글에 댓글 작성."""
    # 수동 입력 필요: 댓글 입력 영역 CSS 셀렉터
    COMMENT_INPUT_SELECTOR = ".comment_inbox .comment_input"
    COMMENT_SUBMIT_SELECTOR = ".comment_inbox .btn_register"
    try:
        driver.get(article_url)
        time.sleep(2)
        inp = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, COMMENT_INPUT_SELECTOR))
        )
        inp.click()
        inp.send_keys(comment_text)
        driver.find_element(By.CSS_SELECTOR, COMMENT_SUBMIT_SELECTOR).click()
        time.sleep(2)
        logger.info(f"댓글 작성 완료: {comment_text[:20]}...")
        return True
    except Exception as e:
        logger.error(f"댓글 작성 실패: {e}")
        return False


def get_article_list(driver: webdriver.Chrome, cafe_id: str, menu_id: str,
                     page: int = 1) -> list[dict]:
    """게시판의 게시글 목록 가져오기."""
    # 수동 입력 필요: 게시글 목록 CSS 셀렉터
    ARTICLE_ROW_SELECTOR = ".article-board .board-list .inner_list"
    ARTICLE_TITLE_SELECTOR = ".article"
    ARTICLE_AUTHOR_GRADE_SELECTOR = ".member_level"

    url = f"https://cafe.naver.com/ArticleList.nhn?search.clubid=&search.menuid={menu_id}&search.page={page}"
    articles = []
    try:
        driver.get(url)
        time.sleep(2)
        rows = driver.find_elements(By.CSS_SELECTOR, ARTICLE_ROW_SELECTOR)
        for row in rows:
            title_el = row.find_elements(By.CSS_SELECTOR, ARTICLE_TITLE_SELECTOR)
            grade_el = row.find_elements(By.CSS_SELECTOR, ARTICLE_AUTHOR_GRADE_SELECTOR)
            href = title_el[0].get_attribute("href") if title_el else ""
            articles.append({
                "title": title_el[0].text.strip() if title_el else "",
                "url": href,
                "author_grade": grade_el[0].get_attribute("alt") if grade_el else "알수없음",
            })
    except Exception as e:
        logger.error(f"게시글 목록 조회 실패: {e}")
    return articles


def filter_articles_by_grade(articles: list[dict], allowed_grades: list[str]) -> list[dict]:
    """답글 등급 필터: 허용된 등급의 게시글만 반환."""
    return [a for a in articles if a.get("author_grade") in allowed_grades]


# ═══════════════════════════════════════════════
# 8. 보조조치 해제
# ═══════════════════════════════════════════════

def check_and_release_auxiliary(driver: webdriver.Chrome, cafe_id: str) -> bool:
    """보조조치 상태 확인 및 자동 해제 시도."""
    # 수동 입력 필요: 보조조치 관련 CSS 셀렉터 / URL
    AUX_CHECK_URL = f"https://cafe.naver.com/{cafe_id}"
    AUX_INDICATOR_SELECTOR = ".restrict_area"
    AUX_RELEASE_BTN_SELECTOR = ".btn_release"
    try:
        driver.get(AUX_CHECK_URL)
        time.sleep(2)
        indicator = driver.find_elements(By.CSS_SELECTOR, AUX_INDICATOR_SELECTOR)
        if not indicator:
            return True  # 보조조치 없음
        release_btn = driver.find_elements(By.CSS_SELECTOR, AUX_RELEASE_BTN_SELECTOR)
        if release_btn:
            release_btn[0].click()
            time.sleep(2)
            logger.info(f"보조조치 해제 완료: {cafe_id}")
            return True
        logger.warning(f"보조조치 해제 버튼 없음: {cafe_id}")
        return False
    except Exception as e:
        logger.error(f"보조조치 해제 실패: {e}")
        return False


# ═══════════════════════════════════════════════
# 9. 2Captcha 캡차 풀기
# ═══════════════════════════════════════════════

def solve_captcha_2captcha(api_key: str, site_key: str, page_url: str) -> Optional[str]:
    """2Captcha API로 reCAPTCHA 풀기."""
    # 수동 입력 필요: site_key는 캡차가 있는 페이지에서 직접 확인 필요
    try:
        # 캡차 요청
        resp = requests.post("http://2captcha.com/in.php", data={
            "key": api_key, "method": "userrecaptcha",
            "googlekey": site_key, "pageurl": page_url, "json": 1
        }).json()
        if resp.get("status") != 1:
            logger.error(f"2Captcha 요청 실패: {resp}")
            return None
        task_id = resp["request"]

        # 결과 폴링
        for _ in range(30):
            time.sleep(5)
            result = requests.get("http://2captcha.com/res.php", params={
                "key": api_key, "action": "get", "id": task_id, "json": 1
            }).json()
            if result.get("status") == 1:
                logger.info("캡차 풀기 성공")
                return result["request"]
            if result.get("request") != "CAPCHA_NOT_READY":
                logger.error(f"캡차 에러: {result}")
                return None
        logger.error("캡차 타임아웃")
        return None
    except Exception as e:
        logger.error(f"2Captcha 에러: {e}")
        return None


# ═══════════════════════════════════════════════
# 10. Gemini AI 원고 생성
# ═══════════════════════════════════════════════

def generate_content_gemini(api_key: str, model_name: str, keyword: str,
                            prompt_template: Optional[str] = None) -> str:
    """Gemini API로 키워드 기반 원고 생성."""
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name)
    prompt = prompt_template or (
        f"'{keyword}' 키워드로 네이버 카페에 올릴 자연스러운 글을 작성해줘. "
        f"광고 느낌 없이 정보성 글로 500자 내외로 작성해."
    )
    try:
        response = model.generate_content(prompt)
        logger.info(f"Gemini 원고 생성 완료 (키워드: {keyword})")
        return response.text
    except Exception as e:
        logger.error(f"Gemini 생성 실패: {e}")
        return ""


# ═══════════════════════════════════════════════
# 11. 구글시트 연동
# ═══════════════════════════════════════════════

GSHEET_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def connect_gsheet(cred_path: str, sheet_url: str) -> gspread.Spreadsheet:
    """구글시트 연결."""
    creds = Credentials.from_service_account_file(cred_path, scopes=GSHEET_SCOPES)
    gc = gspread.authorize(creds)
    spreadsheet = gc.open_by_url(sheet_url)
    logger.info("구글시트 연결 완료")
    return spreadsheet


def read_keywords_from_sheet(spreadsheet: gspread.Spreadsheet, sheet_name: str = "키워드") -> list[str]:
    """키워드 시트에서 키워드 목록 읽기."""
    ws = spreadsheet.worksheet(sheet_name)
    values = ws.col_values(1)  # A열
    keywords = [v.strip() for v in values[1:] if v.strip()]  # 헤더 제외
    logger.info(f"키워드 {len(keywords)}개 로드")
    return keywords


def read_contents_from_sheet(spreadsheet: gspread.Spreadsheet, sheet_name: str = "원고") -> list[dict]:
    """원고 시트에서 제목/본문 읽기."""
    ws = spreadsheet.worksheet(sheet_name)
    records = ws.get_all_records()
    logger.info(f"원고 {len(records)}개 로드")
    return records


def append_result_to_sheet(spreadsheet: gspread.Spreadsheet, sheet_name: str,
                           row: list) -> None:
    """결과를 시트에 한 줄 추가."""
    ws = spreadsheet.worksheet(sheet_name)
    ws.append_row(row)


# ═══════════════════════════════════════════════
# 12. 원고 폴더 로드
# ═══════════════════════════════════════════════

def load_contents_from_folder(folder_path: str) -> list[dict]:
    """원고 폴더에서 텍스트 파일 로드. 파일명=제목, 내용=본문."""
    contents = []
    for fname in sorted(os.listdir(folder_path)):
        fpath = os.path.join(folder_path, fname)
        if os.path.isfile(fpath):
            with open(fpath, "r", encoding="utf-8") as f:
                body = f.read().strip()
            title = os.path.splitext(fname)[0]
            contents.append({"title": title, "content": body})
    logger.info(f"원고 폴더에서 {len(contents)}개 로드")
    return contents



