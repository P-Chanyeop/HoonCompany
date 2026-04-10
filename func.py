"""
func.py — 네이버 카페 자동화 핵심 함수 모음
SOFTCAT | SC-2026-0401-CF
"""

import os
import re
import sys
import time
import random
import base64
import string
import logging
import configparser
from datetime import datetime
from typing import Optional, Callable

import undetected_chromedriver as uc
# from selenium import webdriver
# from selenium.webdriver.chrome.options import Options
# from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.alert import Alert
import pyperclip
import google.generativeai as genai

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s — %(message)s")
logger = logging.getLogger(__name__)

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.ini")


# ═══════════════════════════════════════════════
# 설정 로드
# ═══════════════════════════════════════════════

def load_config():
    cfg = configparser.ConfigParser()
    cfg.read(CONFIG_PATH, encoding="utf-8")
    return cfg


def get_gemini_key():
    cfg = load_config()
    return cfg.get("gemini", "api_key", fallback="").strip()


# ═══════════════════════════════════════════════
# 구글시트에서 계정 로드
# ═══════════════════════════════════════════════

def load_accounts_from_gsheet():
    """구글시트에서 계정 로드 (A:아이디, B:비밀번호, C:성함, D:생년월일, E:성별)"""
    cfg = load_config()
    gs_key = cfg.get("google_sheets", "api_key", fallback="")
    gs_id = cfg.get("google_sheets", "sheet_id", fallback="")
    if not gs_key or not gs_id:
        return []
    try:
        from googleapiclient.discovery import build
        service = build('sheets', 'v4', developerKey=gs_key)
        result = service.spreadsheets().values().get(
            spreadsheetId=gs_id, range='A2:J1000'
        ).execute()
        accounts = []
        for row in result.get('values', []):
            if len(row) >= 2:
                accounts.append({
                    "id": row[0].strip(),
                    "pw": row[1].strip(),
                    "name": row[2].strip() if len(row) > 2 else "",
                    "birth": row[3].strip() if len(row) > 3 else "",
                    "gender": row[4].strip() if len(row) > 4 else "",
                    "cafe_url": row[7].strip() if len(row) > 7 else "",
                    "menu_id": row[8].strip() if len(row) > 8 else "",
                    "post_count": int(row[9].strip()) if len(row) > 9 and row[9].strip().isdigit() else 1,
                })
        logger.info(f"구글시트에서 {len(accounts)}개 계정 로드")
        return accounts
    except Exception as e:
        logger.error(f"구글시트 로드 실패: {e}")
        return []


# ═══════════════════════════════════════════════
# 구글시트 쓰기
# ═══════════════════════════════════════════════

def _get_sheets_service_write():
    """쓰기 가능한 구글시트 서비스 반환. 서비스 계정 JSON 필요."""
    cfg = load_config()
    sa_path = cfg.get("google_sheets", "service_account", fallback="").strip()
    if sa_path and os.path.isfile(sa_path):
        from google.oauth2.service_account import Credentials
        from googleapiclient.discovery import build
        creds = Credentials.from_service_account_file(sa_path, scopes=["https://www.googleapis.com/auth/spreadsheets"])
        return build('sheets', 'v4', credentials=creds)
    return None


def append_to_gsheet(rows, sheet_name="결과", log_fn=None):
    """
    구글시트에 행 추가 (append).

    Args:
        rows: [[col1, col2, ...], ...] 추가할 행 목록
        sheet_name: 시트(탭) 이름 (기본: "결과")
        log_fn: 로그 콜백

    Returns:
        bool: 성공 여부
    """
    _log = log_fn or (lambda msg: logger.info(msg))
    cfg = load_config()
    gs_id = cfg.get("google_sheets", "sheet_id", fallback="")
    if not gs_id:
        _log("구글시트 ID 없음")
        return False
    try:
        service = _get_sheets_service_write()
        if not service:
            _log("구글시트 쓰기 불가 — config.ini [google_sheets] service_account 경로 설정 필요")
            return False
        service.spreadsheets().values().append(
            spreadsheetId=gs_id,
            range=f"{sheet_name}!A1",
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body={"values": rows}
        ).execute()
        _log(f"구글시트 기록 완료: {len(rows)}행 → [{sheet_name}]")
        return True
    except Exception as e:
        _log(f"구글시트 기록 실패: {str(e)[:60]}")
        return False


# ═══════════════════════════════════════════════
# 프록시 로드
# ═══════════════════════════════════════════════

def load_proxies(filepath):
    proxies = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                proxies.append(line)
    return proxies


# ═══════════════════════════════════════════════
# 유틸
# ═══════════════════════════════════════════════

def slow_type(element, text):
    """사람처럼 한 글자씩 랜덤 딜레이로 타이핑."""
    for ch in text:
        element.send_keys(ch)
        time.sleep(0.05 + 0.05 * (hash(ch) % 3))


def dismiss_alert(driver):
    try:
        Alert(driver).accept()
        time.sleep(0.5)
    except:
        pass


def get_page_safe(driver):
    dismiss_alert(driver)
    try:
        return driver.current_url, driver.page_source[:5000]
    except:
        dismiss_alert(driver)
        return driver.current_url, driver.page_source[:5000]


def generate_random_password():
    length = random.randint(10, 14)
    chars = string.ascii_letters + string.digits
    specials = "!@#$%"
    pw = [
        random.choice(string.ascii_uppercase),
        random.choice(string.ascii_lowercase),
        random.choice(string.digits),
        random.choice(specials),
    ]
    pw += [random.choice(chars + specials) for _ in range(length - 4)]
    random.shuffle(pw)
    return "".join(pw)


def save_new_password(nid, new_pw):
    filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), "changed_passwords.txt")
    with open(filepath, "a", encoding="utf-8") as f:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"{nid}\t{new_pw}\t{ts}\n")


# ═══════════════════════════════════════════════
# 브라우저 생성
# ═══════════════════════════════════════════════

def cleanup_workers():
    """이전 실행에서 남은 크롬 프로세스 및 임시 폴더 정리."""
    import subprocess, shutil, tempfile, glob
    # 크롬/크롬드라이버 프로세스 종료
    for proc_name in ["chrome.exe", "chromedriver.exe"]:
        try:
            subprocess.run(["taskkill", "/F", "/IM", proc_name, "/T"],
                           capture_output=True, timeout=5)
        except:
            pass
    time.sleep(1)
    # 임시 폴더 정리
    tmp = tempfile.gettempdir()
    for d in glob.glob(os.path.join(tmp, "uc_worker_*")):
        try:
            shutil.rmtree(d, ignore_errors=True)
        except:
            pass
    logger.info("워커 정리 완료")


def create_driver(proxy_str=None, worker_id=0, chrome_version=145):
    import tempfile
    opts = uc.ChromeOptions()
    if proxy_str:
        opts.add_argument(f"--proxy-server={proxy_str}")
    opts.add_argument("--disable-backgrounding-occluded-windows")
    opts.add_argument("--disable-renderer-backgrounding")
    user_data = os.path.join(tempfile.gettempdir(), f"uc_worker_{worker_id}")

    # 생성 시도, 실패하면 정리 후 재시도
    for attempt in range(2):
        try:
            driver = uc.Chrome(options=opts, version_main=chrome_version, user_data_dir=user_data)
            driver.set_window_size(1920, 1080)
            driver.set_page_load_timeout(20)
            driver.implicitly_wait(5)
            return driver
        except Exception as e:
            if attempt == 0:
                logger.warning(f"드라이버 생성 실패 (워커#{worker_id}), 정리 후 재시도: {str(e)[:40]}")
                import subprocess, shutil
                try:
                    subprocess.run(["taskkill", "/F", "/IM", "chrome.exe", "/T"],
                                   capture_output=True, timeout=5)
                except:
                    pass
                time.sleep(1)
                try:
                    shutil.rmtree(user_data, ignore_errors=True)
                except:
                    pass
                time.sleep(1)
            else:
                raise


# def create_driver(proxy_str=None, worker_id=0):
#     import tempfile
#     opts = Options()
#     if proxy_str:
#         opts.add_argument(f"--proxy-server={proxy_str}")
#     user_data = os.path.join(tempfile.gettempdir(), f"uc_worker_{worker_id}")
#     opts.add_argument(f"--user-data-dir={user_data}")
#
#     for attempt in range(2):
#         try:
#             driver = webdriver.Chrome(options=opts)
#             driver.set_window_size(1920, 1080)
#             driver.set_page_load_timeout(20)
#             driver.implicitly_wait(5)
#             return driver
#         except Exception as e:
#             if attempt == 0:
#                 logger.warning(f"드라이버 생성 실패 (워커#{worker_id}), 정리 후 재시도: {str(e)[:40]}")
#                 import subprocess, shutil
#                 try:
#                     subprocess.run(["taskkill", "/F", "/IM", "chrome.exe", "/T"],
#                                    capture_output=True, timeout=5)
#                 except:
#                     pass
#                 time.sleep(1)
#                 try:
#                     shutil.rmtree(user_data, ignore_errors=True)
#                 except:
#                     pass
#                 time.sleep(1)
#             else:
#                 raise


# ═══════════════════════════════════════════════
# 네이버 로그인
# ═══════════════════════════════════════════════

LOGIN_URL = "https://nid.naver.com/nidlogin.login?mode=form&url=https%3A%2F%2Fwww.naver.com"


def naver_login(driver, account, log_fn=None):
    """
    네이버 로그인. 캡차/보호조치 자동 처리.
    반환: {"ok": bool, "msg": str, "error": str|None}
    """
    _log = log_fn or (lambda msg: logger.info(msg))
    nid = account["id"]

    try:
        driver.get(LOGIN_URL)
        time.sleep(1)
        dismiss_alert(driver)

        # 포커스
        driver.switch_to.window(driver.current_window_handle)
        driver.execute_script("window.focus();")
        time.sleep(0.2)

        # ID/PW 입력
        id_input = driver.find_element(By.CSS_SELECTOR, "#id")
        id_input.click()
        time.sleep(0.1)
        slow_type(id_input, account["id"])
        time.sleep(0.3)

        pw_input = driver.find_element(By.CSS_SELECTOR, "#pw")
        pw_input.click()
        time.sleep(0.1)
        slow_type(pw_input, account["pw"])
        time.sleep(0.3)

        driver.find_element(By.CSS_SELECTOR, ".btn_login").click()
        time.sleep(2)

        url, page = get_page_safe(driver)

        # ── 보호조치 ──
        if "비정상적인 활동" in page or "보호(잠금) 조치" in page or "보호하고 있습니다" in page or "idSafetyRelease" in url:
            return _handle_protection(driver, account, url, page, _log)

        # ── 이용제한 ──
        if "이용제한" in page or "이용 제한" in page:
            return {"ok": False, "msg": "이용제한", "error": "blocked_unknown"}

        # ── 로그인 성공 ──
        if "nid.naver.com" not in url and "nidlogin" not in url:
            return {"ok": True, "msg": f"로그인 성공 - {url[:50]}", "error": None}

        # ── 캡차 ──
        if "captcha" in page.lower() or "영수증" in page or "정답을 입력" in page or "빈 칸을 채워" in page:
            return _handle_captcha(driver, account, _log)

        # ── 에러 메시지 ──
        err_msg = ""
        try:
            err_el = driver.find_element(By.CSS_SELECTOR, ".message_text, #err_common, .error_message")
            err_msg = err_el.text.strip().replace("\n", " ")
        except:
            pass
        return {"ok": False, "msg": f"로그인 실패 — {err_msg}" if err_msg else f"로그인 실패 (URL: {url[:50]})", "error": "login_fail"}

    except Exception as e:
        return {"ok": False, "msg": str(e)[:80], "error": "exception"}


# ═══════════════════════════════════════════════
# 보호조치 처리
# ═══════════════════════════════════════════════

def _handle_protection(driver, account, url, page, _log):
    nid = account["id"]
    btns = driver.find_elements(By.CSS_SELECTOR, "a, button, div[role='button'], span")
    for btn in btns:
        try:
            txt = btn.text.strip()
            if "본인 확인" in txt:
                return {"ok": False, "msg": "보호조치 - 핸드폰 인증 (해제 불가)", "error": "blocked_phone"}
            if "보호조치 해제" in txt or "보호 조치 해제" in txt:
                btn.click()
                time.sleep(3)
                dismiss_alert(driver)
                # 바로 생년월일 입력 시도 (login_test_uc.py와 동일)
                if account.get("name") and account.get("birth"):
                    result = _solve_birthday(driver, account, _log)
                    if result:
                        return result
                return {"ok": False, "msg": "보호조치 - 생년월일 인증 (개인정보 없음)", "error": "blocked_birthday"}
        except:
            continue
    return {"ok": False, "msg": "영구정지 (해제 불가)", "error": "permanent_ban"}


def _solve_birthday(driver, account, _log):
    """생년월일 입력 - 비밀번호 변경 - 2단계 인증 스킵 - 재로그인."""
    name = account.get("name", "")
    birth = account.get("birth", "")
    gender = account.get("gender", "")

    parts = birth.replace("-", ".").split(".")
    if len(parts) != 3:
        return None
    year, month, day = parts

    try:
        # 이름
        name_input = driver.find_elements(By.CSS_SELECTOR, "input[placeholder*='이름'], input[title*='이름'], input[name*='name']")
        if name_input:
            name_input[0].click()
            time.sleep(0.2)
            pyperclip.copy(name)
            name_input[0].send_keys(Keys.CONTROL, "a")
            name_input[0].send_keys(Keys.CONTROL, "v")
            time.sleep(0.3)
            _log(f"이름 입력: {name}")

        # 성별
        if gender:
            for btn in driver.find_elements(By.CSS_SELECTOR, "label, button, span, div"):
                try:
                    txt = btn.text.strip()
                    if (gender == "남" and txt == "남자") or (gender == "여" and txt == "여자"):
                        btn.click()
                        _log(f"성별 선택: {txt}")
                        break
                except:
                    continue
            time.sleep(0.3)

        # 년도
        year_input = driver.find_elements(By.CSS_SELECTOR, "input[placeholder*='년'], input[title*='년']")
        if year_input:
            year_input[0].click()
            time.sleep(0.2)
            pyperclip.copy(year)
            year_input[0].send_keys(Keys.CONTROL, "a")
            year_input[0].send_keys(Keys.CONTROL, "v")
            time.sleep(0.2)
            _log(f"년도 입력: {year}")

        # 월 (JS)
        month_val = str(int(month)).zfill(2)
        driver.execute_script(f"""
            var sel = document.getElementById('birthMonth');
            if (sel) {{ sel.value = '{month_val}'; sel.dispatchEvent(new Event('change')); }}
        """)
        time.sleep(0.2)
        _log(f"월 선택: {int(month)}월")

        # 일
        day_input = driver.find_elements(By.CSS_SELECTOR, "input[placeholder*='일'], input[title*='일']")
        if day_input:
            day_input[0].click()
            time.sleep(0.2)
            pyperclip.copy(str(int(day)))
            day_input[0].send_keys(Keys.CONTROL, "a")
            day_input[0].send_keys(Keys.CONTROL, "v")
            time.sleep(0.2)
            _log(f"일 입력: {int(day)}")

        # 확인 버튼
        for btn in driver.find_elements(By.CSS_SELECTOR, "button, a, input[type='submit']"):
            try:
                if btn.text.strip() == "확인":
                    btn.click()
                    time.sleep(3)
                    break
            except:
                continue

        # 비밀번호 변경 페이지
        url3, page3 = get_page_safe(driver)
        if "비밀번호를 변경" in page3 or "새 비밀번호" in page3:
            new_pw = generate_random_password()
            _log(f"새 비밀번호 생성: {new_pw}")

            pw_inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='password']")
            if len(pw_inputs) >= 2:
                pw_inputs[0].click()
                time.sleep(0.1)
                slow_type(pw_inputs[0], new_pw)
                time.sleep(0.2)
                pw_inputs[1].click()
                time.sleep(0.1)
                slow_type(pw_inputs[1], new_pw)
                time.sleep(0.2)

            # 자동입력 방지 (최대 3회)
            for try_i in range(3):
                if _solve_text_captcha(driver, _log):
                    for btn in driver.find_elements(By.CSS_SELECTOR, "button, a, input[type='submit']"):
                        try:
                            if btn.text.strip() == "확인":
                                btn.click()
                                time.sleep(3)
                                break
                        except:
                            continue
                    url4, page4 = get_page_safe(driver)
                    if "잘못된 자동입력" in page4 or "다시 입력" in page4:
                        _log(f"자동입력 방지 문자 틀림 ({try_i+1}/3)")
                        continue
                    break

            # 2단계 인증 - 나중에 하기
            time.sleep(2)
            url5, page5 = get_page_safe(driver)
            if "2단계 인증" in page5 or "나중에 하기" in page5:
                for btn in driver.find_elements(By.CSS_SELECTOR, "button, a"):
                    try:
                        if "나중에 하기" in btn.text.strip():
                            btn.click()
                            _log("2단계 인증 - 나중에 하기")
                            time.sleep(2)
                            break
                    except:
                        continue

            save_new_password(account["id"], new_pw)
            account["pw"] = new_pw
            _log(f"비밀번호 변경 저장 완료")

            # 재로그인
            url6, page6 = get_page_safe(driver)
            if "nidlogin" in url6 or "로그인" in page6:
                _log("바뀐 비밀번호로 재로그인...")
                driver.switch_to.window(driver.current_window_handle)
                driver.execute_script("window.focus();")
                id_input = driver.find_element(By.CSS_SELECTOR, "#id")
                id_input.click()
                slow_type(id_input, account["id"])
                time.sleep(0.2)
                pw_input = driver.find_element(By.CSS_SELECTOR, "#pw")
                pw_input.click()
                slow_type(pw_input, new_pw)
                time.sleep(0.2)
                driver.find_element(By.CSS_SELECTOR, ".btn_login").click()
                time.sleep(3)
                url7, _ = get_page_safe(driver)
                if "nid.naver.com" not in url7:
                    _log("재로그인 성공!")
                    return {"ok": True, "msg": f"보호조치 해제 + 재로그인 성공", "error": None}

        return {"ok": False, "msg": "보호조치 - 생년월일 입력 완료", "error": "blocked_birthday"}

    except Exception as e:
        _log(f"생년월일 입력 실패: {str(e)[:60]}")
        return None


# ═══════════════════════════════════════════════
# 캡차 처리
# ═══════════════════════════════════════════════

def _handle_captcha(driver, account, _log):
    nid = account["id"]
    gemini_key = get_gemini_key()
    if not gemini_key:
        return {"ok": False, "msg": "캡차 발생 (Gemini 키 없음)", "error": "captcha"}

    if _solve_receipt_captcha(driver, account, gemini_key, _log):
        url2, _ = get_page_safe(driver)
        if "nid.naver.com" not in url2 and "nidlogin" not in url2:
            return {"ok": True, "msg": f"캡차 풀고 로그인 성공 - {url2[:50]}", "error": None}
    return {"ok": False, "msg": "캡차 풀기 실패", "error": "captcha"}


def _solve_receipt_captcha(driver, account, gemini_key, _log):
    try:
        captcha_img = driver.find_elements(By.CSS_SELECTOR, "#captchaimg")
        if not captcha_img:
            captcha_img = driver.find_elements(By.CSS_SELECTOR, ".captcha_img")
        if not captcha_img:
            return False

        # 질문
        question = ""
        q_el = driver.find_elements(By.CSS_SELECTOR, "#captcha_info, .captcha_message")
        if q_el:
            question = q_el[0].text.strip()
        _log(f"캡차 질문: {question[:50]}")

        # Gemini
        img_b64 = captcha_img[0].screenshot_as_base64
        genai.configure(api_key=gemini_key)
        model = genai.GenerativeModel("gemini-2.5-pro")

        import PIL.Image, io
        img = PIL.Image.open(io.BytesIO(base64.b64decode(img_b64)))

        prompt = f"""이 영수증 이미지를 보고 아래 질문에 답해주세요.
질문: {question}
영수증에 적힌 내용을 정확히 읽고 정답만 짧게 답하세요. 설명 없이 정답만."""

        response = model.generate_content([prompt, img])
        answer = re.sub(r'[^\w가-힣]', '', response.text.strip())
        _log(f"Gemini 답변: {answer}")

        # 입력
        input_el = driver.find_elements(By.CSS_SELECTOR, "#captcha")
        if not input_el:
            input_el = driver.find_elements(By.CSS_SELECTOR, "#chptcha")
        if input_el:
            input_el[0].click()
            time.sleep(0.2)
            pyperclip.copy(answer)
            input_el[0].send_keys(Keys.CONTROL, "a")
            input_el[0].send_keys(Keys.CONTROL, "v")
            time.sleep(0.3)

        # 비밀번호 재입력
        if account:
            pw_input = driver.find_elements(By.CSS_SELECTOR, "#pw")
            if pw_input:
                pw_input[0].click()
                time.sleep(0.2)
                pyperclip.copy(account["pw"])
                pw_input[0].send_keys(Keys.CONTROL, "a")
                pw_input[0].send_keys(Keys.CONTROL, "v")
                time.sleep(0.3)

        driver.find_element(By.CSS_SELECTOR, ".btn_login").click()
        time.sleep(3)
        return True

    except Exception as e:
        _log(f"캡차 풀기 실패: {str(e)[:60]}")
        return False


def _solve_text_captcha(driver, _log):
    gemini_key = get_gemini_key()
    if not gemini_key:
        return False
    try:
        captcha_imgs = driver.find_elements(By.CSS_SELECTOR, "img[src*='captcha'], img.captcha_img, #captchaimg")
        if not captcha_imgs:
            return False

        img_b64 = captcha_imgs[0].screenshot_as_base64
        genai.configure(api_key=gemini_key)
        model = genai.GenerativeModel("gemini-2.5-pro")

        import PIL.Image, io
        img = PIL.Image.open(io.BytesIO(base64.b64decode(img_b64)))

        prompt = """이 이미지에 보이는 텍스트/문자를 정확히 읽어주세요.
왜곡된 글자입니다. 보이는 영문자와 숫자만 정확히 답해주세요. 설명 없이 문자만."""

        response = model.generate_content([prompt, img])
        answer = re.sub(r'[^a-zA-Z0-9]', '', response.text.strip())
        _log(f"캡차 문자 인식: {answer}")

        captcha_input = driver.find_elements(By.CSS_SELECTOR, "#autoValue")
        if not captcha_input:
            captcha_input = driver.find_elements(By.CSS_SELECTOR, "input[name='autoValue']")
        if captcha_input:
            captcha_input[0].click()
            time.sleep(0.1)
            slow_type(captcha_input[0], answer)
            return True
    except Exception as e:
        _log(f"텍스트 캡차 실패: {str(e)[:60]}")
    return False


# ═══════════════════════════════════════════════
# 카페 접속
# ═══════════════════════════════════════════════

def get_cafe_grades(driver, cafe_url, log_fn=None):
    """카페 등급 조회 — 카페 접속 → clubid 추출 → API로 등급 조회."""
    _log = log_fn or (lambda msg: logger.info(msg))
    empty = {"my_grade": -1, "my_grade_text": "", "grades": {}}
    try:
        driver.get(cafe_url)
        time.sleep(3)
        dismiss_alert(driver)

        # clubid 추출
        club_id = None
        try:
            link = driver.find_element(By.CSS_SELECTOR, 'a[name="myCafeUrlLink"]')
            m = re.search(r'clubid=(\d+)', link.get_attribute("href") or "")
            if m: club_id = m.group(1)
        except:
            pass
        if not club_id:
            m = re.search(r'clubid["\s:=]+(\d+)', driver.page_source[:10000])
            if m: club_id = m.group(1)
        if not club_id:
            _log("clubid 추출 실패")
            return empty
        _log(f"clubid={club_id}")

        # API 호출 (브라우저 XHR)
        import json
        api_url = f"https://apis.naver.com/cafe-web/cafe-mobile/CafeMemberLevelInfo?cafeId={club_id}"
        resp_text = driver.execute_script(
            "var x=new XMLHttpRequest();x.open('GET',arguments[0],false);x.send();return x.responseText;",
            api_url
        )
        data = json.loads(resp_text)
        result = data.get("message", {}).get("result", {})
        level_list = result.get("memberLevelList", [])
        if not level_list:
            _log("등급 목록 비어있음")
            return empty

        grade_info = {"my_grade": -1, "my_grade_text": "", "grades": {}, "grade_order": {}, "is_member": result.get("isCafeMember", False)}
        for idx, lv in enumerate(level_list):
            level, name = lv["memberlevel"], lv["memberlevelname"]
            conds = []
            if lv.get("visitcount"): conds.append(f"방문{lv['visitcount']}")
            if lv.get("articlecount"): conds.append(f"글{lv['articlecount']}")
            if lv.get("commentcount"): conds.append(f"댓글{lv['commentcount']}")
            if lv.get("likecount"): conds.append(f"좋아요{lv['likecount']}")
            cond_str = ", ".join(conds) if conds else "자동/수동"
            grade_info["grades"][level] = f"{name} ({cond_str})"
            grade_info["grade_order"][idx] = {"level": level, "name": name, "cond": cond_str}
            _log(f"등급 {idx}: {name} — {cond_str}")
            if lv.get("existmember") == "Y":
                grade_info["my_grade"] = idx
                grade_info["my_grade_text"] = name

        _log(f"등급 조회 완료: {len(grade_info['grades'])}개, 가입={grade_info['is_member']}, 내등급={grade_info['my_grade_text'] or '없음'}")
        return grade_info

    except Exception as e:
        _log(f"등급 조회 실패: {str(e)[:60]}")
        return empty


def _close_cafe_popups(driver):
    """카페 접속 시 뜨는 팝업(가입 환영 등) 닫기."""
    try:
        # 닫기/X 버튼 찾기
        close_selectors = [
            "button.btn_close", "a.btn_close", ".popup_close",
            "button[class*='close']", "a[class*='close']",
            "button[title='닫기']", "a[title='닫기']",
        ]
        for sel in close_selectors:
            btns = driver.find_elements(By.CSS_SELECTOR, sel)
            for btn in btns:
                try:
                    if btn.is_displayed():
                        btn.click()
                        time.sleep(0.5)
                except:
                    continue
        # 텍스트가 "닫기"인 버튼
        for btn in driver.find_elements(By.CSS_SELECTOR, "button, a"):
            try:
                if btn.text.strip() == "닫기" and btn.is_displayed():
                    btn.click()
                    time.sleep(0.5)
            except:
                continue
    except:
        pass


def visit_cafe(driver, account, log_fn=None):
    """
    로그인된 드라이버로 카페 접속.
    반환: {"ok": bool, "msg": str, "cafe_id": str, "menu_id": str}
    """
    _log = log_fn or (lambda msg: logger.info(msg))
    cafe_url = account.get("cafe_url", "")
    menu_id = account.get("menu_id", "")

    if not cafe_url:
        return {"ok": False, "msg": "카페 URL 없음"}

    try:
        _log(f"카페 접속: {cafe_url}")
        driver.get(cafe_url)
        time.sleep(3)
        dismiss_alert(driver)

        # 팝업 닫기 (가입 환영 등 카페별 팝업)
        _close_cafe_popups(driver)

        url, page = get_page_safe(driver)
        _log(f"카페 현재 URL: {url}")

        # 디버깅: 카페 페이지 소스 저장
        try:
            with open("cafe_debug.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)
        except:
            pass

        # 카페 접속 확인
        if "cafe.naver.com" not in url:
            return {"ok": False, "msg": f"카페 접속 실패 (URL: {url[:50]})"}

        # 카페 가입 여부 확인 — a._rosRestrict onclick으로 판별
        is_member = False
        try:
            ros_btns = driver.find_elements(By.CSS_SELECTOR, "a._rosRestrict")
            for btn in ros_btns:
                onclick = btn.get_attribute("onclick") or ""
                if "writeBoard" in onclick:
                    is_member = True
                    break
                elif "joinCafe" in onclick:
                    is_member = False
                    break
        except:
            pass

        # 폴백: 페이지 소스에서 판별
        if not is_member:
            if "writeBoard" in page:
                is_member = True

        if not is_member:
            _log("카페 미가입 상태")
            return {"ok": False, "msg": "카페 미가입", "need_join": True}

        _log("카페 가입 확인")

        # 메뉴 ID가 있으면 해당 게시판으로 이동
        if menu_id:
            board_url = f"{cafe_url}?iframe_url=/ArticleList.nhn%3Fsearch.clubid=%26search.menuid={menu_id}"
            driver.get(board_url)
            time.sleep(2)
            _log(f"지정 게시판 이동: 메뉴ID={menu_id}")
            return {"ok": True, "msg": f"카페 접속 + 게시판 이동 (메뉴ID: {menu_id})", "menu_id": menu_id}

        # 메뉴 ID 없으면 자동 탐색은 나중에 구현
        return {"ok": True, "msg": "카페 접속 성공 (게시판 미지정)", "menu_id": ""}

    except Exception as e:
        return {"ok": False, "msg": f"카페 접속 에러: {str(e)[:60]}"}


# ═══════════════════════════════════════════════
# 게시글 목록 가져오기
# ═══════════════════════════════════════════════

def find_writable_board(driver, cafe_url, log_fn=None):
    """카페에서 글쓰기 가능한 게시판 자동 탐색 (API). 메뉴ID 반환."""
    _log = log_fn or (lambda msg: logger.info(msg))
    try:
        # clubid 가져오기
        driver.get(cafe_url)
        time.sleep(3)
        dismiss_alert(driver)
        _close_cafe_popups(driver)

        page = driver.page_source
        match = re.search(r'clubid["\s:=]+(\d+)', page)
        if not match:
            _log("clubid 못 찾음")
            return ""
        clubid = match.group(1)

        # 메뉴 API 호출
        api_url = f"https://apis.naver.com/cafe-web/cafe-cafemain-api/v1.0/cafes/{clubid}/menus"
        result = driver.execute_script(f"""
            var xhr = new XMLHttpRequest();
            xhr.open('GET', '{api_url}', false);
            xhr.send();
            return xhr.responseText;
        """)

        import json
        data = json.loads(result)
        menus = data.get("message", {}).get("result", {}).get("menus", [])

        # menuType "B" (일반 게시판)만 필터
        boards = [m for m in menus if m.get("menuType") == "B"]
        _log(f"게시판 {len(boards)}개 발견")

        if boards:
            # 첫 번째 일반 게시판 반환
            board = boards[0]
            _log(f"글쓰기 가능 게시판: {board['name']} (메뉴ID: {board['menuId']})")
            return str(board["menuId"])

        _log("글쓰기 가능한 게시판 없음")
        return ""

    except Exception as e:
        _log(f"게시판 탐색 실패: {str(e)[:60]}")
        return ""


def get_article_list(driver, cafe_url, menu_id, page=1, log_fn=None):
    """지정 게시판의 게시글 목록 가져오기."""
    _log = log_fn or (lambda msg: logger.info(msg))
    articles = []
    try:
        # 게시판 페이지 접속
        board_url = f"{cafe_url}/ArticleList.nhn?search.clubid=&search.menuid={menu_id}&search.page={page}"
        driver.get(f"{cafe_url}?iframe_url=/ArticleList.nhn%3Fsearch.menuid%3D{menu_id}%26search.page%3D{page}")
        time.sleep(3)

        # iframe 전환
        try:
            iframe = driver.find_element(By.CSS_SELECTOR, "iframe#cafe_main")
            driver.switch_to.frame(iframe)
            time.sleep(1)
        except:
            pass

        # 게시글 행 파싱
        rows = driver.find_elements(By.CSS_SELECTOR, ".article-board .board-list .inner_list, tr.board-list-item")
        for row in rows:
            try:
                # 제목 + 링크
                title_el = row.find_elements(By.CSS_SELECTOR, "a.article")
                if not title_el:
                    continue
                title = title_el[0].text.strip()
                href = title_el[0].get_attribute("href") or ""

                # 글번호 추출
                article_id = ""
                match = re.search(r'articleid=(\d+)', href)
                if match:
                    article_id = match.group(1)

                # 작성자 등급
                grade_el = row.find_elements(By.CSS_SELECTOR, "img.mem_level, .member_level, .level_icon")
                grade_alt = ""
                if grade_el:
                    grade_alt = grade_el[0].get_attribute("alt") or grade_el[0].get_attribute("title") or ""

                articles.append({
                    "title": title,
                    "article_id": article_id,
                    "href": href,
                    "author_grade": grade_alt,
                })
            except:
                continue

        driver.switch_to.default_content()
        _log(f"게시글 {len(articles)}개 수집 (페이지 {page})")
        return articles

    except Exception as e:
        _log(f"게시글 목록 실패: {str(e)[:60]}")
        try:
            driver.switch_to.default_content()
        except:
            pass
        return []


# ═══════════════════════════════════════════════
# 답글 작성
# ═══════════════════════════════════════════════

def write_reply(driver, cafe_url, article_id, content, log_fn=None):
    """게시글에 답글(댓글) 작성."""
    _log = log_fn or (lambda msg: logger.info(msg))
    try:
        # 게시글 접속
        article_url = f"{cafe_url}?iframe_url=/ArticleRead.nhn%3Farticleid%3D{article_id}"
        driver.get(article_url)
        time.sleep(3)

        # iframe 전환
        try:
            iframe = driver.find_element(By.CSS_SELECTOR, "iframe#cafe_main")
            driver.switch_to.frame(iframe)
            time.sleep(1)
        except:
            pass

        # 댓글 입력 영역 찾기
        comment_input = driver.find_elements(By.CSS_SELECTOR, ".comment_inbox .comment_input, textarea.comment_input")
        if not comment_input:
            # 에디터 클릭해서 활성화
            comment_area = driver.find_elements(By.CSS_SELECTOR, ".comment_box, .CommentWriter")
            if comment_area:
                comment_area[0].click()
                time.sleep(1)
                comment_input = driver.find_elements(By.CSS_SELECTOR, ".comment_inbox .comment_input, textarea.comment_input")

        if not comment_input:
            _log("댓글 입력 영역 못 찾음")
            driver.switch_to.default_content()
            return False

        # 댓글 입력
        comment_input[0].click()
        time.sleep(0.3)
        pyperclip.copy(content)
        comment_input[0].send_keys(Keys.CONTROL, "a")
        comment_input[0].send_keys(Keys.CONTROL, "v")
        time.sleep(0.5)

        # 등록 버튼 클릭
        submit_btn = driver.find_elements(By.CSS_SELECTOR, ".btn_register, button.btn_submit, a.btn_register")
        if submit_btn:
            submit_btn[0].click()
            time.sleep(2)
            _log(f"답글 작성 완료: {content[:20]}...")
            driver.switch_to.default_content()
            return True
        else:
            _log("등록 버튼 못 찾음")
            driver.switch_to.default_content()
            return False

    except Exception as e:
        _log(f"답글 작성 실패: {str(e)[:60]}")
        try:
            driver.switch_to.default_content()
        except:
            pass
        return False


# ═══════════════════════════════════════════════
# 카페 작업 실행 (OFF 모드: 지정 게시판 답글)
# ═══════════════════════════════════════════════

def do_cafe_work(driver, account, cafe_grades, settings, log_fn=None):
    """
    카페 작업 실행.
    - OFF 모드 (menu_id 있음): 지정 게시판 → 답글
    - ON 모드 (menu_id 없음): 글쓰기 가능 게시판 자동 탐색 → 답글
    """
    _log = log_fn or (lambda msg: logger.info(msg))
    cafe_url = account.get("cafe_url", "")
    menu_id = account.get("menu_id", "")
    post_count = account.get("post_count", 1)

    # 메뉴ID 없으면 자동 탐색
    if not menu_id:
        _log("메뉴ID 없음 - 글쓰기 가능 게시판 자동 탐색")
        menu_id = find_writable_board(driver, cafe_url, _log)
        if not menu_id:
            _log("글쓰기 가능한 게시판 못 찾음")
            return {"ok": False, "msg": "글쓰기 가능 게시판 없음", "written": 0}

    written = 0
    contents = settings.get("contents", [])
    if not contents:
        _log("원고 없음")
        return {"ok": False, "msg": "원고 없음", "written": 0}

    page_lo = settings.get("page_lo", 1)
    page_hi = settings.get("page_hi", 10)
    delay_lo = settings.get("delay_lo", 3)
    delay_hi = settings.get("delay_hi", 8)
    grade_filter = settings.get("grade_filter", list(range(6)))

    # 카페 등급 정보
    grade_info = cafe_grades.get(cafe_url, {})
    grade_order = grade_info.get("grade_order", {})

    for page in range(page_lo, page_hi + 1):
        if written >= post_count:
            break

        _log(f"페이지 {page} 게시글 수집 중...")
        articles = get_article_list(driver, cafe_url, menu_id, page, _log)

        for article in articles:
            if written >= post_count:
                break

            # 등급 필터 (TODO: 작성자 등급과 grade_order 매핑 필요)
            # 지금은 필터 없이 진행

            # 원고 선택 (순환)
            content = contents[written % len(contents)]

            _log(f"답글 작성: [{article['title'][:20]}] article_id={article['article_id']}")
            success = write_reply(driver, cafe_url, article["article_id"], content, _log)

            if success:
                written += 1
                _log(f"답글 {written}/{post_count} 완료")

                # 딜레이
                delay = random.randint(delay_lo, delay_hi)
                _log(f"딜레이 {delay}초...")
                time.sleep(delay)

    _log(f"카페 작업 완료: {written}/{post_count}개 작성")
    return {"ok": written > 0, "msg": f"{written}/{post_count}개 작성", "written": written}
