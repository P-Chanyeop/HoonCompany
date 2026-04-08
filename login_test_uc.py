"""
네이버 로그인 테스트 (undetected-chromedriver 버전)

사용법:
  pip install undetected-chromedriver
  python login_test_uc.py ..\네이버id.txt ..\프록시고정_하이아이피.txt --workers 50
"""

import sys
import os
import re
import time
import random
import base64
import argparse
import configparser
from datetime import datetime

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.alert import Alert
from selenium.webdriver.common.keys import Keys
import pyperclip
import google.generativeai as genai

LOGIN_URL = "https://nid.naver.com/nidlogin.login?mode=form&url=https%3A%2F%2Fwww.naver.com"
TIMEOUT = 20
GEMINI_API_KEY = ""  # --gemini-key 인자로 받음


def load_accounts(filepath):
    """구글시트에서 계정 정보 로드 (A:아이디, B:비밀번호, C:성함, D:생년월일, E:성별)"""
    cfg = configparser.ConfigParser()
    cfg.read(os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.ini"), encoding="utf-8")
    gs_key = cfg.get("google_sheets", "api_key", fallback="")
    gs_id = cfg.get("google_sheets", "sheet_id", fallback="")

    accounts = []

    # 구글시트에서 읽기 시도
    if gs_key and gs_id:
        try:
            from googleapiclient.discovery import build
            service = build('sheets', 'v4', developerKey=gs_key)
            result = service.spreadsheets().values().get(
                spreadsheetId=gs_id, range='A2:E1000'
            ).execute()
            for row in result.get('values', []):
                if len(row) >= 2:
                    acc = {
                        "id": row[0].strip(),
                        "pw": row[1].strip(),
                        "name": row[2].strip() if len(row) > 2 else "",
                        "birth": row[3].strip() if len(row) > 3 else "",
                        "gender": row[4].strip() if len(row) > 4 else "",
                    }
                    accounts.append(acc)
            print(f"  📊 구글시트에서 {len(accounts)}개 계정 로드")
        except Exception as e:
            print(f"  ⚠️ 구글시트 로드 실패: {e}")

    # 구글시트 실패 시 종료
    if not accounts:
        log("❌ 구글시트 연결 실패. 프로그램 종료.", "ERROR")
        sys.exit(1)

    for i, a in enumerate(accounts[:3]):
        print(f"  [DEBUG] #{i+1} ID='{a['id']}' 이름='{a['name']}' 생년월일='{a['birth']}' 성별='{a['gender']}'")
    return accounts


def load_proxies(filepath):
    proxies = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                proxies.append(line)
    return proxies


def create_driver(proxy_str=None, worker_id=0):
    opts = uc.ChromeOptions()
    if proxy_str:
        opts.add_argument(f"--proxy-server={proxy_str}")
    import tempfile
    user_data = os.path.join(tempfile.gettempdir(), f"uc_worker_{worker_id}")
    driver = uc.Chrome(options=opts, version_main=145, user_data_dir=user_data)
    driver.set_window_size(1920, 1080)
    driver.set_page_load_timeout(TIMEOUT)
    driver.implicitly_wait(5)
    return driver


def dismiss_alert(driver):
    """alert 있으면 닫기. 없으면 무시."""
    try:
        Alert(driver).accept()
        time.sleep(0.5)
    except:
        pass


def get_page_safe(driver):
    """alert 처리 후 안전하게 page_source 가져오기."""
    dismiss_alert(driver)
    try:
        return driver.current_url, driver.page_source[:5000]
    except:
        dismiss_alert(driver)
        return driver.current_url, driver.page_source[:5000]


def log(msg, level="INFO"):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {level} — {msg}")


def slow_type(element, text):
    """사람처럼 한 글자씩 랜덤 딜레이로 타이핑."""
    for ch in text:
        element.send_keys(ch)
        time.sleep(0.05 + 0.05 * (hash(ch) % 3))



def solve_birthday_release(driver, account):
    """보호조치 해제 페이지에서 이름/성별/생년월일 입력."""
    name = account.get("name", "")
    birth = account.get("birth", "")
    gender = account.get("gender", "")

    if not name or not birth:
        print(f"    ⚠️ 이름 또는 생년월일 정보 없음")
        return False

    parts = birth.replace("-", ".").split(".")
    if len(parts) != 3:
        print(f"    ⚠️ 생년월일 형식 오류: {birth}")
        return False
    year, month, day = parts[0], parts[1], parts[2]

    try:
        # 디버깅: 페이지 소스 저장
        with open("birthday_debug.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)

        # 이름 입력
        name_input = driver.find_elements(By.CSS_SELECTOR, "input[placeholder*='이름'], input[title*='이름'], input[name*='name']")
        if name_input:
            name_input[0].click()
            time.sleep(0.2)
            pyperclip.copy(name)
            name_input[0].send_keys(Keys.CONTROL, "a")
            name_input[0].send_keys(Keys.CONTROL, "v")
            time.sleep(0.3)
            print(f"    ✏️ 이름 입력: {name}")

        # 성별 선택
        if gender:
            btns = driver.find_elements(By.CSS_SELECTOR, "label, button, span, div")
            for btn in btns:
                try:
                    txt = btn.text.strip()
                    if gender == "남" and txt == "남자":
                        btn.click()
                        print(f"    ✏️ 성별 선택: 남자")
                        break
                    elif gender == "여" and txt == "여자":
                        btn.click()
                        print(f"    ✏️ 성별 선택: 여자")
                        break
                except:
                    continue
            time.sleep(0.3)

        # 년도 입력
        year_input = driver.find_elements(By.CSS_SELECTOR, "input[placeholder*='년'], input[title*='년']")
        if year_input:
            year_input[0].click()
            time.sleep(0.2)
            pyperclip.copy(year)
            year_input[0].send_keys(Keys.CONTROL, "a")
            year_input[0].send_keys(Keys.CONTROL, "v")
            time.sleep(0.2)
            print(f"    ✏️ 년도 입력: {year}")

        # 월 선택 (JS로 직접 — 로딩 타이밍 문제 방지)
        month_val = str(int(month)).zfill(2)
        driver.execute_script(f"""
            var sel = document.getElementById('birthMonth');
            if (sel) {{ sel.value = '{month_val}'; sel.dispatchEvent(new Event('change')); }}
        """)
        time.sleep(0.2)
        print(f"    ✏️ 월 선택: {int(month)}월")

        # 일 입력
        day_input = driver.find_elements(By.CSS_SELECTOR, "input[placeholder*='일'], input[title*='일']")
        if not day_input:
            # 모든 input에서 찾기
            all_inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='text'], input[type='number'], input[type='tel']")
            for inp in all_inputs:
                ph = (inp.get_attribute("placeholder") or "").strip()
                if "일" in ph:
                    day_input = [inp]
                    break
        if day_input:
            day_input[0].click()
            time.sleep(0.2)
            pyperclip.copy(str(int(day)))
            day_input[0].send_keys(Keys.CONTROL, "a")
            day_input[0].send_keys(Keys.CONTROL, "v")
            time.sleep(0.2)
            print(f"    ✏️ 일 입력: {int(day)}")
        else:
            print(f"    ⚠️ 일 입력 필드 못 찾음")

        # 확인 버튼 클릭
        confirm_btns = driver.find_elements(By.CSS_SELECTOR, "button, a, input[type='submit']")
        for btn in confirm_btns:
            try:
                txt = btn.text.strip()
                if txt == "확인":
                    btn.click()
                    print(f"    ✅ 확인 버튼 클릭")
                    time.sleep(3)
                    break
            except:
                continue

        # 비밀번호 변경 페이지 처리
        url3, page3 = get_page_safe(driver)
        if "비밀번호를 변경" in page3 or "새 비밀번호" in page3:
            new_pw = _generate_random_password()
            print(f"    🔑 새 비밀번호 생성: {new_pw}")

            # 새 비밀번호 입력
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
                print(f"    ✏️ 새 비밀번호 입력 완료")

            # 자동입력 방지 문자 (최대 3회 시도)
            for captcha_try in range(3):
                captcha_solved = _solve_text_captcha(driver)
                if not captcha_solved:
                    break

                print(f"    🤖 자동입력 방지 문자 입력 완료 (시도 {captcha_try + 1}/3)")

                # 확인 버튼 클릭
                for btn in driver.find_elements(By.CSS_SELECTOR, "button, a, input[type='submit']"):
                    try:
                        if btn.text.strip() == "확인":
                            btn.click()
                            time.sleep(3)
                            break
                    except:
                        continue

                # 결과 확인
                url4, page4 = get_page_safe(driver)
                if "잘못된 자동입력" in page4 or "다시 입력" in page4:
                    print(f"    ❌ 자동입력 방지 문자 틀림 (시도 {captcha_try + 1}/3)")
                    continue
                else:
                    break  # 성공 또는 다음 페이지로 이동

            # 2단계 인증 설정 페이지 → "나중에 하기" 클릭
            time.sleep(2)
            url5, page5 = get_page_safe(driver)
            if "2단계 인증" in page5 or "나중에 하기" in page5:
                for btn in driver.find_elements(By.CSS_SELECTOR, "button, a"):
                    try:
                        if "나중에 하기" in btn.text.strip():
                            btn.click()
                            print(f"    ⏭️ 2단계 인증 → 나중에 하기 클릭")
                            time.sleep(2)
                            break
                    except:
                        continue

            # 비밀번호 변경 결과 저장
            _save_new_password(account["id"], new_pw)
            print(f"    💾 비밀번호 저장: changed_passwords.txt")
            account["pw"] = new_pw

            # 바뀐 비밀번호로 다시 로그인
            url6, page6 = get_page_safe(driver)
            if "nidlogin" in url6 or "로그인" in page6:
                print(f"    🔄 바뀐 비밀번호로 재로그인 시도...")
                driver.switch_to.window(driver.current_window_handle)
                driver.execute_script("window.focus();")
                time.sleep(0.2)
                id_input = driver.find_element(By.CSS_SELECTOR, "#id")
                id_input.click()
                time.sleep(0.1)
                slow_type(id_input, account["id"])
                time.sleep(0.2)
                pw_input = driver.find_element(By.CSS_SELECTOR, "#pw")
                pw_input.click()
                time.sleep(0.1)
                slow_type(pw_input, new_pw)
                time.sleep(0.2)
                driver.find_element(By.CSS_SELECTOR, ".btn_login").click()
                time.sleep(3)
                url7, page7 = get_page_safe(driver)
                if "nid.naver.com" not in url7 and "nidlogin" not in url7:
                    print(f"    ✅ 재로그인 성공!")

        print(f"    📋 생년월일 해제 완료: {name} / {gender} / {birth}")
        return True

    except Exception as e:
        print(f"    ⚠️ 생년월일 입력 실패: {str(e)[:60]}")
        return False


def _generate_random_password():
    """랜덤 비밀번호 생성 (영문+숫자+특수문자, 10~14자)."""
    import string
    length = random.randint(10, 14)
    chars = string.ascii_letters + string.digits
    specials = "!@#$%"
    # 최소 1개씩 보장
    pw = [
        random.choice(string.ascii_uppercase),
        random.choice(string.ascii_lowercase),
        random.choice(string.digits),
        random.choice(specials),
    ]
    pw += [random.choice(chars + specials) for _ in range(length - 4)]
    random.shuffle(pw)
    return "".join(pw)


def _solve_text_captcha(driver):
    """자동입력 방지 문자 이미지를 Gemini로 풀기."""
    if not GEMINI_API_KEY:
        return False
    try:
        # 캡차 이미지 찾기
        captcha_imgs = driver.find_elements(By.CSS_SELECTOR, "img[src*='captcha'], img.captcha_img, #captchaimg")
        if not captcha_imgs:
            return False

        img_b64 = captcha_imgs[0].screenshot_as_base64

        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel("gemini-2.5-pro")

        import PIL.Image
        import io
        img_bytes = base64.b64decode(img_b64)
        img = PIL.Image.open(io.BytesIO(img_bytes))

        prompt = """이 이미지에 보이는 텍스트/문자를 정확히 읽어주세요.
왜곡된 글자입니다. 보이는 영문자와 숫자만 정확히 답해주세요.
설명 없이 문자만 답하세요."""

        response = model.generate_content([prompt, img])
        answer = response.text.strip()
        answer_clean = re.sub(r'[^a-zA-Z0-9]', '', answer)
        print(f"    🤖 캡차 문자 인식: '{answer}' → '{answer_clean}'")

        # 입력
        captcha_input = driver.find_elements(By.CSS_SELECTOR, "#autoValue")
        if not captcha_input:
            captcha_input = driver.find_elements(By.CSS_SELECTOR, "input[name='autoValue'], input[placeholder*='자동입력']")
        if captcha_input:
            captcha_input[0].click()
            time.sleep(0.1)
            slow_type(captcha_input[0], answer_clean)
            return True
    except Exception as e:
        print(f"    ⚠️ 텍스트 캡차 풀기 실패: {str(e)[:60]}")
    return False


def _save_new_password(nid, new_pw):
    """변경된 비밀번호를 파일에 저장."""
    filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), "changed_passwords.txt")
    with open(filepath, "a", encoding="utf-8") as f:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"{nid}\t{new_pw}\t{ts}\n")

def click_release_button(driver):
    """보호조치 해제 / 이용제한 해제 버튼 찾아서 클릭."""
    try:
        # 방법1: 텍스트로 찾기
        btns = driver.find_elements(By.CSS_SELECTOR, "a, button, div[role='button'], span")
        for btn in btns:
            try:
                txt = btn.text.strip()
                if "해제" in txt and btn.is_displayed():
                    btn.click()
                    time.sleep(3)
                    dismiss_alert(driver)
                    return True
            except:
                continue
        # 방법2: href에 idSafetyRelease 포함된 링크
        links = driver.find_elements(By.CSS_SELECTOR, "a[href*='idSafetyRelease']")
        if links:
            links[0].click()
            time.sleep(3)
            dismiss_alert(driver)
            return True
    except:
        pass
    return False


def check_release_page(driver, worker_id, nid, prefix="보호조치"):
    """해제 페이지에서 생년월일/핸드폰 판별."""
    url2, page2 = get_page_safe(driver)

    # 핸드폰 먼저 체크 (둘 다 있는 페이지에서 생년월일 선택 가능하면 생년월일 우선)
    has_birthday = "생년월일" in page2
    has_phone = ("휴대전화" in page2 or "휴대폰" in page2 or "인증번호" in page2
                 or "전화번호" in page2 or "+82" in page2 or "이용제한 해제" in page2)

    if has_birthday and has_phone:
        # 둘 다 있으면 생년월일로 풀 수 있음
        return {"worker": worker_id, "id": nid, "ok": False,
                "msg": f"🔒 {prefix} → 생년월일 인증 (해제 가능)", "error": "blocked_birthday"}
    elif has_birthday:
        return {"worker": worker_id, "id": nid, "ok": False,
                "msg": f"🔒 {prefix} → 생년월일 인증 (해제 가능)", "error": "blocked_birthday"}
    elif has_phone:
        return {"worker": worker_id, "id": nid, "ok": False,
                "msg": f"🔒 {prefix} → 📱 핸드폰 인증 (못풂)", "error": "blocked_phone"}
    else:
        return {"worker": worker_id, "id": nid, "ok": False,
                "msg": f"🔒 {prefix} (해제 방식 불명) URL={url2[:60]}", "error": "blocked_unknown"}



def solve_receipt_captcha(driver, account=None):
    """영수증 캡차 감지 및 Gemini로 풀기. 성공하면 True."""
    if not GEMINI_API_KEY:
        return False

    try:
        # 디버깅: 페이지 소스 저장
        with open("captcha_debug.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        print("    📄 captcha_debug.html 저장됨")

        # 캡차 이미지 찾기
        captcha_img = driver.find_elements(By.CSS_SELECTOR, "#captchaimg")
        if not captcha_img:
            captcha_img = driver.find_elements(By.CSS_SELECTOR, ".captcha_img, img[src*='captcha']")
        if not captcha_img:
            print("    ⚠️ 캡차 이미지 못 찾음")
            return False

        # 질문 텍스트 추출
        page = driver.page_source
        question = ""
        # 정확한 셀렉터로 질문 가져오기
        q_el = driver.find_elements(By.CSS_SELECTOR, "#captcha_info, .captcha_message")
        if q_el:
            question = q_el[0].text.strip()
        if not question:
            match = re.search(r'([^<>]{5,}?\[.\??\][^<>]{0,30})', page)
            if match:
                question = match.group(1).strip()

        print(f"    📝 질문: '{question[:60]}'")

        # 이미지 스크린샷 (base64)
        img_b64 = captcha_img[0].screenshot_as_base64

        # Gemini API 호출
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel("gemini-2.5-pro")

        import PIL.Image
        import io
        img_bytes = base64.b64decode(img_b64)
        img = PIL.Image.open(io.BytesIO(img_bytes))

        if question:
            prompt = f"""이 영수증 이미지를 보고 아래 질문에 답해주세요.

질문: {question}

영수증에 적힌 내용을 정확히 읽고 질문에 맞는 정답만 답해주세요.
숫자, 단어, 주소 등 정답만 짧게 답하세요. 설명 없이 정답만."""
        else:
            prompt = """이 영수증 이미지에 질문이 있습니다.
영수증을 읽고 빈칸에 들어갈 정답만 짧게 답해주세요. 설명 없이 정답만."""

        response = model.generate_content([prompt, img])
        answer = response.text.strip()
        answer_clean = re.sub(r'[^\w가-힣]', '', answer)

        print(f"    🤖 Gemini 답변: '{answer}' → 정제: '{answer_clean}'")

        # 정답 입력 (pyperclip 복붙)
        input_el = driver.find_elements(By.CSS_SELECTOR, "#captcha")
        if not input_el:
            input_el = driver.find_elements(By.CSS_SELECTOR, "#chptcha")
        if input_el:
            input_el[0].click()
            time.sleep(0.2)
            pyperclip.copy(answer_clean)
            input_el[0].send_keys(Keys.CONTROL, "a")
            input_el[0].send_keys(Keys.CONTROL, "v")
            time.sleep(0.3)

            # 비밀번호 다시 입력
            if account:
                pw_input = driver.find_elements(By.CSS_SELECTOR, "#pw")
                if pw_input:
                    pw_input[0].click()
                    time.sleep(0.2)
                    pyperclip.copy(account["pw"])
                    pw_input[0].send_keys(Keys.CONTROL, "a")
                    pw_input[0].send_keys(Keys.CONTROL, "v")
                    time.sleep(0.3)
                    
                    pw_input[0].send_keys(Keys.ENTER)

            # driver.find_element(By.CSS_SELECTOR, ".btn_login").click()
            time.sleep(3)
            return True
        else:
            print("    ⚠️ 정답 입력 필드 못 찾음")
            return False

    except Exception as e:
        print(f"    ⚠️ 캡차 풀기 실패: {str(e)[:60]}")
    return False

def login_with_driver(worker_id, account, driver):
    nid = account["id"]
    try:
        driver.get(LOGIN_URL)
        time.sleep(1)
        dismiss_alert(driver)

        # 창 포커스 가져오기
        driver.switch_to.window(driver.current_window_handle)
        driver.execute_script("window.focus();")
        time.sleep(0.2)

        # ID/PW 입력 — 사람처럼 타이핑
        id_input = driver.find_element(By.CSS_SELECTOR, "#id")
        id_input.click()
        time.sleep(0.2)
        slow_type(id_input, account["id"])
        time.sleep(0.3)

        pw_input = driver.find_element(By.CSS_SELECTOR, "#pw")
        pw_input.click()
        time.sleep(0.2)
        slow_type(pw_input, account["pw"])
        time.sleep(0.3)

        driver.find_element(By.CSS_SELECTOR, ".btn_login").click()
        time.sleep(2)

        url, page = get_page_safe(driver)

        # 1) 보호조치
        if "비정상적인 활동" in page or "보호(잠금) 조치" in page or "보호하고 있습니다" in page or "idSafetyRelease" in url:
            # 버튼 텍스트로 판별
            btns = driver.find_elements(By.CSS_SELECTOR, "a, button, div[role='button'], span")
            for btn in btns:
                try:
                    txt = btn.text.strip()
                    if "본인 확인" in txt:
                        return {"worker": worker_id, "id": nid, "ok": False,
                                "msg": "🔒 보호조치 → 📱 핸드폰 인증 (못풂)", "error": "blocked_phone"}
                    if "보호조치 해제" in txt or "보호 조치 해제" in txt:
                        # 해제 버튼 클릭 → 해제 페이지 이동
                        btn.click()
                        time.sleep(3)
                        dismiss_alert(driver)
                        # 생년월일 입력 시도
                        if account.get("name") and account.get("birth"):
                            if solve_birthday_release(driver, account):
                                return {"worker": worker_id, "id": nid, "ok": False,
                                        "msg": "🔒 보호조치 → 생년월일 입력 완료 (확인 필요)", "error": "blocked_birthday"}
                        return {"worker": worker_id, "id": nid, "ok": False,
                                "msg": "🔒 보호조치 → 생년월일 인증 (개인정보 없음)", "error": "blocked_birthday"}
                except:
                    continue
            return {"worker": worker_id, "id": nid, "ok": False,
                    "msg": "🔒 영구정지 (해제 불가)", "error": "permanent_ban"}

        # 2) 이용제한
        if "이용제한" in page or "이용 제한" in page:
            if click_release_button(driver):
                return check_release_page(driver, worker_id, nid, "이용제한")
            return {"worker": worker_id, "id": nid, "ok": False,
                    "msg": "🔒 이용제한 (해제 버튼 못찾음)", "error": "blocked_unknown"}

        # 3) 로그인 성공
        if "nid.naver.com" not in url and "nidlogin" not in url:
            return {"worker": worker_id, "id": nid, "ok": True,
                    "msg": f"로그인 성공 → {url[:50]}", "error": None}

        # 4) 캡차 → Gemini로 풀기 시도 (최대 2회)
        for captcha_try in range(1):
            if not ("captcha" in url or "captcha" in page.lower() or "영수증" in page or "정답을 입력" in page or "빈 칸을 채워" in page):
                break
            print(f"    🔄 캡차 시도 {captcha_try + 1}/2")
            if solve_receipt_captcha(driver, account):
                url, page = get_page_safe(driver)
                if "nid.naver.com" not in url and "nidlogin" not in url:
                    return {"worker": worker_id, "id": nid, "ok": True,
                            "msg": f"🤖 캡차 풀고 로그인 성공 (시도 {captcha_try + 1}회) → {url[:50]}", "error": None}
                # 실패했으면 page 갱신해서 다음 루프에서 다시 캡차 감지
            else:
                break  # solve 자체가 실패하면 재시도 의미 없음

        if "captcha" in url or "captcha" in page.lower() or "영수증" in page or "정답을 입력" in page:
            return {"worker": worker_id, "id": nid, "ok": False,
                    "msg": "🤖 캡차 시도 실패", "error": "captcha"}

        # 5) 보안 인증
        if "보안" in page or "새로운 기기" in page:
            return {"worker": worker_id, "id": nid, "ok": False,
                    "msg": "보안 인증 필요", "error": "security"}

        # 6) 기타 실패 — 에러 메시지 확인
        err_msg = ""
        try:
            err_el = driver.find_element(By.CSS_SELECTOR, ".message_text, #err_common, .error_message")
            err_msg = err_el.text.strip().replace("\n", " ")
        except:
            pass
        return {"worker": worker_id, "id": nid, "ok": False,
                "msg": f"로그인 실패 — {err_msg}" if err_msg else f"로그인 실패 (URL: {url[:50]})", "error": "login_fail"}

    except Exception as e:
        return {"worker": worker_id, "id": nid, "ok": False,
                "msg": str(e)[:80], "error": "exception"}


def main():
    parser = argparse.ArgumentParser(description="네이버 로그인 테스트 (UC)")
    parser.add_argument("--account-file", default="", help="계정 파일 (구글시트 우선)")
    parser.add_argument("proxy_file", help="프록시 파일")
    parser.add_argument("--workers", type=int, default=50, help="워커 수 (기본: 50)")
    parser.add_argument("--only", default="", help="특정 ID만 실행 (쉼표 구분, 예: aotmnurz1389,buryut)")
    parser.add_argument("--gemini-key", default="", help="Gemini API 키 (캡차 풀기용)")
    args = parser.parse_args()

    global GEMINI_API_KEY
    # config.ini에서 읽기, 인자가 있으면 인자 우선
    if args.gemini_key:
        GEMINI_API_KEY = args.gemini_key
    else:
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.ini")
        if os.path.isfile(config_path):
            cfg = configparser.ConfigParser()
            cfg.read(config_path, encoding="utf-8")
            GEMINI_API_KEY = cfg.get("gemini", "api_key", fallback="").strip()
            if GEMINI_API_KEY:
                log(f"config.ini에서 Gemini API 키 로드 완료")

    accounts = load_accounts(args.account_file)
    if args.only:
        only_ids = [x.strip() for x in args.only.split(",")]
        accounts = [a for a in accounts if a["id"] in only_ids]
        log(f"--only 필터: {only_ids} → {len(accounts)}개 계정")
    proxies = load_proxies(args.proxy_file)
    random.shuffle(proxies)
    log(f"계정 {len(accounts)}개 / 프록시 {len(proxies)}개 로드 (랜덤 배정)")

    count = min(args.workers, len(accounts), len(proxies))
    log(f"=== 네이버 로그인 테스트 UC ({count}개) ===")

    results = []
    drivers = []

    for i in range(count):
        print(f"\n  워커#{i+1:2d} 🔌 프록시={proxies[i]} / ID={accounts[i]['id']}")
        try:
            d = create_driver(proxies[i], i)
            r = login_with_driver(i, accounts[i], d)
            results.append(r)
            status = "✅" if r["ok"] else "❌"
            print(f"  워커#{i+1:2d} {status} [{r['id']}] {r['msg']}")

            if r.get("error") in ("blocked_phone", "permanent_ban", "login_fail", "exception"):
                try:
                    d.quit()
                except:
                    pass
            else:
                drivers.append((i, d))
        except Exception as e:
            print(f"  워커#{i+1:2d} ❌ [{accounts[i]['id']}] {str(e)[:60]}")

    ok = [r for r in results if r["ok"]]
    bday = [r for r in results if r.get("error") == "blocked_birthday"]
    phone = [r for r in results if r.get("error") == "blocked_phone"]
    blocked_etc = [r for r in results if r.get("error") == "permanent_ban"]
    captcha = [r for r in results if r.get("error") == "captcha"]
    security = [r for r in results if r.get("error") == "security"]
    fail = [r for r in results if not r["ok"] and r.get("error") not in
            ("captcha", "security", "blocked_birthday", "blocked_phone", "permanent_ban")]

    print()
    log(f"결과: 성공 {len(ok)} | 생년월일(해제가능) {len(bday)} | 핸드폰(못풂) {len(phone)} | 영구정지 {len(blocked_etc)} | 캡차 {len(captcha)} | 보안인증 {len(security)} | 실패 {len(fail)} / 총 {count}개")

    if drivers:
        input("Enter 누르면 모든 브라우저 종료...")
        for i, d in drivers:
            try:
                d.quit()
            except:
                pass


if __name__ == "__main__":
    main()
