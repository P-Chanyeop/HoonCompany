"""
카페 가입 기능 테스트 스크립트
- 선택형(radio) + 서술형(textarea) 질문 처리
- 캡차 이미지 Gemini 2.5 Pro로 풀기 (최대 3회)
- 동의 후 가입하기 버튼 클릭 안 함
"""
import time
import base64
import pyperclip
import google.generativeai as genai
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

import func
from cafe_join import check_membership, _navigate_to_join_page, _fill_nickname, _accept_terms, _switch_to_cafe_iframe

# ── 설정 ──
TEST_CAFE_URL = "https://cafe.naver.com/dokchi"
PROXY = None


def log(msg):
    from datetime import datetime
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def handle_join_questions(driver):
    """join_qna_area 기반 질문 처리 (선택형 + 서술형)"""
    _switch_to_cafe_iframe(driver)

    areas = driver.find_elements(By.CSS_SELECTOR, ".join_qna_area > div")
    if not areas:
        log("가입 질문 없음")
        return

    log(f"가입 질문 {len(areas)}개 발견")

    gemini_key = func.get_gemini_key()
    genai.configure(api_key=gemini_key)
    model = genai.GenerativeModel("gemini-2.5-flash")

    for area in areas:
        # 질문 텍스트
        q_el = area.find_elements(By.CSS_SELECTOR, ".question_text")
        q_text = q_el[0].text.strip() if q_el else ""
        if not q_text:
            continue

        # answer 속성이 있으면 그대로 사용
        answer_attr = area.get_attribute("answer")

        # 선택형 (radio)
        radios = area.find_elements(By.CSS_SELECTOR, "input[type='radio']")
        if radios:
            labels = area.find_elements(By.CSS_SELECTOR, ".answer_list label")
            options = [lbl.text.strip() for lbl in labels]
            log(f"[선택] Q: {q_text[:50]}...")
            log(f"  선택지: {options}")

            # Gemini로 최적 선택지 결정
            prompt = (
                f"네이버 카페 가입 질문입니다. 가장 적절한 선택지 번호(1부터)를 숫자만 답하세요.\n"
                f"질문: {q_text}\n선택지:\n" +
                "\n".join(f"{i+1}. {o}" for i, o in enumerate(options))
            )
            resp = model.generate_content(prompt)
            try:
                idx = int(resp.text.strip()) - 1
            except:
                idx = 0
            idx = max(0, min(idx, len(radios) - 1))

            driver.execute_script("arguments[0].click();", radios[idx])
            log(f"  → 선택: {options[idx] if idx < len(options) else idx}")
            time.sleep(0.3)
            continue

        # 서술형 (textarea / input)
        ta = area.find_elements(By.CSS_SELECTOR, "textarea, input[type='text']")
        if ta:
            if answer_attr:
                answer = answer_attr.strip()
                log(f"[서술] Q: {q_text[:50]}... → answer 속성 사용")
            else:
                prompt = (
                    f"네이버 카페 가입 질문에 답변해주세요.\n"
                    f"질문: {q_text}\n"
                    f"규칙: 자연스럽고 성의있는 한국어 1~2문장. 답변만 출력."
                )
                resp = model.generate_content(prompt)
                answer = resp.text.strip()
                log(f"[서술] Q: {q_text[:50]}... → Gemini 생성")

            ta[0].click()
            time.sleep(0.2)
            pyperclip.copy(answer)
            ta[0].send_keys(Keys.CONTROL, "a")
            ta[0].send_keys(Keys.CONTROL, "v")
            log(f"  → A: {answer[:50]}")
            time.sleep(0.3)


def solve_captcha(driver, max_attempts=3):
    """캡차 이미지를 Gemini 2.5 Pro로 풀기. 최대 max_attempts회 시도."""
    _switch_to_cafe_iframe(driver)

    gemini_key = func.get_gemini_key()
    genai.configure(api_key=gemini_key)
    model = genai.GenerativeModel("gemini-2.5-pro")

    for attempt in range(1, max_attempts + 1):
        log(f"캡차 시도 {attempt}/{max_attempts}")

        # 재시도 시 새로고침 버튼 클릭
        if attempt > 1:
            try:
                refresh_btn = driver.find_element(By.CSS_SELECTOR, ".join_captcha_info button .join_captcha_refresh")
                refresh_btn.find_element(By.XPATH, "./ancestor::button").click()
                log("  캡차 새로고침...")
                time.sleep(2)
            except:
                log("  새로고침 버튼 못 찾음")

        # 캡차 이미지 찾기
        img_el = driver.find_elements(By.CSS_SELECTOR, ".join_captcha_area img")
        if not img_el:
            log("캡차 이미지 없음 — 스킵")
            return True

        # 이미지를 base64로 캡처
        img_b64 = img_el[0].screenshot_as_base64

        # Gemini 2.5 Pro로 캡차 텍스트 추출
        prompt = (
            "이 이미지는 네이버 캡차입니다. 이미지에 보이는 문자를 정확히 읽어주세요.\n"
            "규칙:\n"
            "- 배경 노이즈와 줄을 무시하고 실제 글자만 읽으세요\n"
            "- 대소문자를 정확히 구분하세요\n"
            "- 글자만 출력하세요 (설명, 따옴표, 공백 없이)"
        )
        resp = model.generate_content([
            prompt,
            {"mime_type": "image/png", "data": base64.b64decode(img_b64) if isinstance(img_b64, str) else img_b64}
        ])
        captcha_text = resp.text.strip()
        log(f"  캡차 인식: {captcha_text}")

        # 캡차 입력
        captcha_input = driver.find_element(By.CSS_SELECTOR, "#captcha")
        captcha_input.clear()
        time.sleep(0.2)
        captcha_input.send_keys(captcha_text)
        log(f"  캡차 입력 완료")
        time.sleep(0.3)
        return True

    return False


def main():
    # 1) 계정 로드
    log("구글시트에서 계정 로드...")
    accounts = func.load_accounts_from_gsheet()
    if not accounts:
        log("계정 없음. config.ini 확인")
        return
    acc = accounts[0]
    log(f"테스트 계정: {acc['id']}")

    # 2) 프록시
    proxy = PROXY
    if not proxy:
        cfg = func.load_config()
        proxy_path = cfg.get("paths", "proxy_file", fallback="")
        if proxy_path:
            proxies = func.load_proxies(proxy_path)
            if proxies:
                proxy = proxies[0]
    log(f"프록시: {proxy or '없음'}")

    # 3) 드라이버 + 로그인
    log("드라이버 생성...")
    driver = func.create_driver(proxy, worker_id=99)

    log("로그인 중...")
    login_result = func.naver_login(driver, acc, log)
    if not login_result["ok"]:
        log(f"로그인 실패: {login_result['msg']}")
        driver.quit()
        return
    log("로그인 성공!")

    # 4) 가입 여부 확인
    log(f"가입 여부 확인: {TEST_CAFE_URL}")
    membership = check_membership(driver, TEST_CAFE_URL, log)
    log(f"결과: {membership}")

    if membership["is_member"]:
        log("이미 가입된 카페")
        driver.quit()
        return

    # 5) 가입 페이지 이동
    log("가입 페이지 이동...")
    club_id = membership.get("club_id")
    if not _navigate_to_join_page(driver, TEST_CAFE_URL, club_id, log):
        log("가입 페이지 이동 실패")
        driver.quit()
        return
    time.sleep(2)

    # 6) 닉네임 (기본 닉네임 사용)
    _fill_nickname(driver, None, log)

    # 7) 가입 질문 처리
    log("가입 질문 처리...")
    handle_join_questions(driver)

    # 8) 캡차 처리
    log("캡차 처리...")
    solve_captcha(driver, max_attempts=3)

    # 9) 약관 동의
    log("약관 동의...")
    _accept_terms(driver, log)

    # 10) 가입 버튼 클릭 안 함 (테스트)
    log("⚠️ 테스트 모드: 가입 버튼 클릭하지 않음")

    input("\n브라우저 확인 후 Enter로 종료...")
    driver.quit()


if __name__ == "__main__":
    main()
