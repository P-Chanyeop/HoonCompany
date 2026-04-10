"""
cafe_join.py — 네이버 카페 자동 가입 기능 모듈
SOFTCAT | SC-2026-0401-CF

사용법:
    import func
    from cafe_join import join_cafe, batch_join_cafes

    driver = func.create_driver(proxy, worker_id)
    func.naver_login(driver, account, log_fn)

    # 단일 카페 가입
    result = join_cafe(driver, "https://cafe.naver.com/dokchi", log_fn=print)

    # 다수 계정 일괄 가입
    results = batch_join_cafes(workers, cafe_urls, log_fn=print)

의존성:
    - func.py (dismiss_alert, get_page_safe, get_gemini_key, get_cafe_grades)
    - selenium, google.generativeai, pyperclip
"""

import re
import json
import time
import random
import logging
import base64
from typing import Optional, Callable

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import pyperclip
import google.generativeai as genai

import func

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════
# 카페 가입 여부 확인
# ═══════════════════════════════════════════════

def check_membership(driver, cafe_url, log_fn=None):
    """
    카페 가입 여부를 확인한다.

    Args:
        driver: 로그인된 셀레니움 드라이버
        cafe_url: 카페 URL (예: "https://cafe.naver.com/dokchi")
        log_fn: 로그 콜백 함수 (선택)

    Returns:
        dict: {
            "is_member": bool,      # 가입 여부
            "club_id": str|None,    # 카페 고유 ID (숫자)
            "cafe_url": str,        # 입력된 카페 URL
            "msg": str              # 상태 메시지
        }
    """
    _log = log_fn or (lambda msg: logger.info(msg))
    try:
        driver.get(cafe_url)
        time.sleep(3)
        func.dismiss_alert(driver)

        # clubid 추출
        club_id = _extract_club_id(driver)

        # API로 가입 여부 확인
        if club_id:
            try:
                api_url = f"https://apis.naver.com/cafe-web/cafe-mobile/CafeMemberLevelInfo?cafeId={club_id}"
                resp = driver.execute_script(
                    "var x=new XMLHttpRequest();x.open('GET',arguments[0],false);x.send();return x.responseText;",
                    api_url
                )
                data = json.loads(resp)
                is_member = data.get("message", {}).get("result", {}).get("isCafeMember", False)
                _log(f"가입 여부 확인: {'회원' if is_member else '미가입'} (clubid={club_id})")
                return {"is_member": is_member, "club_id": club_id, "cafe_url": cafe_url, "msg": "회원" if is_member else "미가입"}
            except:
                pass

        # 폴백: a._rosRestrict onclick으로 판별
        is_member = False
        try:
            for btn in driver.find_elements(By.CSS_SELECTOR, "a._rosRestrict"):
                onclick = btn.get_attribute("onclick") or ""
                if "writeBoard" in onclick:
                    is_member = True
                    break
                elif "joinCafe" in onclick:
                    break
        except:
            pass

        _log(f"가입 여부 확인: {'회원' if is_member else '미가입'}")
        return {"is_member": is_member, "club_id": club_id, "cafe_url": cafe_url, "msg": "회원" if is_member else "미가입"}

    except Exception as e:
        _log(f"가입 여부 확인 실패: {str(e)[:60]}")
        return {"is_member": False, "club_id": None, "cafe_url": cafe_url, "msg": str(e)[:60]}


# ═══════════════════════════════════════════════
# 카페 가입
# ═══════════════════════════════════════════════

def join_cafe(driver, cafe_url, nickname=None, log_fn=None):
    """
    네이버 카페에 가입한다. 가입 질문이 있으면 Gemini로 자동 응답.

    Args:
        driver: 로그인된 셀레니움 드라이버
        cafe_url: 카페 URL (예: "https://cafe.naver.com/dokchi")
        nickname: 카페 닉네임 (None이면 네이버 기본 닉네임 사용)
        log_fn: 로그 콜백 함수 (선택)

    Returns:
        dict: {
            "ok": bool,             # 가입 성공 여부
            "msg": str,             # 결과 메시지
            "error": str|None,      # 에러 코드 (already_member, private_cafe, join_failed 등)
            "club_id": str|None,    # 카페 고유 ID
            "cafe_url": str         # 카페 URL
        }
    """
    _log = log_fn or (lambda msg: logger.info(msg))
    result_base = {"cafe_url": cafe_url, "club_id": None}

    try:
        # 1) 카페 접속 및 가입 여부 확인
        membership = check_membership(driver, cafe_url, _log)
        club_id = membership["club_id"]
        result_base["club_id"] = club_id

        if membership["is_member"]:
            _log("이미 가입된 카페")
            return {**result_base, "ok": True, "msg": "이미 가입된 카페", "error": "already_member"}

        # 2) 가입 페이지로 이동
        if not _navigate_to_join_page(driver, cafe_url, club_id, _log):
            return {**result_base, "ok": False, "msg": "가입 페이지 이동 실패", "error": "nav_failed"}

        time.sleep(2)
        url, page = func.get_page_safe(driver)

        # 비공개 카페 체크
        if "비공개" in page or "멤버만" in page:
            _log("비공개 카페 — 가입 불가")
            return {**result_base, "ok": False, "msg": "비공개 카페", "error": "private_cafe"}

        # 3) 닉네임 입력
        _fill_nickname(driver, nickname, _log)

        # 4) 가입 질문 처리 (있는 경우)
        _handle_join_questions(driver, _log)

        # 5) 캡차 처리
        _solve_captcha(driver, _log)

        # 6) 가입 약관 동의
        _accept_terms(driver, _log)

        # 7) 가입 버튼 클릭
        if not _click_join_button(driver, _log):
            return {**result_base, "ok": False, "msg": "가입 버튼 클릭 실패", "error": "join_failed"}

        time.sleep(3)
        func.dismiss_alert(driver)

        # 8) 가입 결과 확인
        url2, page2 = func.get_page_safe(driver)

        # 성공 판별
        if "가입을 축하" in page2 or "가입이 완료" in page2 or "가입 완료" in page2:
            _log("카페 가입 성공!")
            return {**result_base, "ok": True, "msg": "가입 성공", "error": None}

        # 가입 승인 대기
        if "승인" in page2 or "가입 신청" in page2:
            _log("가입 신청 완료 (승인 대기)")
            return {**result_base, "ok": True, "msg": "가입 신청 완료 (승인 대기)", "error": None}

        # 이미 가입
        if "이미 가입" in page2 or "이미 회원" in page2:
            _log("이미 가입된 카페")
            return {**result_base, "ok": True, "msg": "이미 가입된 카페", "error": "already_member"}

        # 에러 메시지 추출
        err = _extract_error_message(driver)
        _log(f"가입 결과 불명: {err or url2[:60]}")
        return {**result_base, "ok": False, "msg": err or f"가입 결과 불명 ({url2[:50]})", "error": "join_failed"}

    except Exception as e:
        _log(f"카페 가입 에러: {str(e)[:60]}")
        return {**result_base, "ok": False, "msg": str(e)[:80], "error": "exception"}


# ═══════════════════════════════════════════════
# 일괄 가입 (멀티워커)
# ═══════════════════════════════════════════════

def batch_join_cafes(workers, cafe_urls, nickname_fn=None, log_fn=None):
    """
    다수 워커로 다수 카페에 병렬 가입한다.

    Args:
        workers: [(worker_idx, account, driver), ...] 로그인된 워커 목록
        cafe_urls: [str, ...] 가입할 카페 URL 목록
        nickname_fn: (account) -> str 닉네임 생성 함수 (선택, None이면 기본 닉네임)
        log_fn: 로그 콜백 함수 (선택)

    Returns:
        list[dict]: 각 (워커, 카페) 조합별 가입 결과 리스트
            [{
                "worker_idx": int,
                "account_id": str,
                "cafe_url": str,
                "ok": bool,
                "msg": str,
                "error": str|None
            }, ...]
    """
    import concurrent.futures

    _log = log_fn or (lambda msg: logger.info(msg))
    results = []

    # 워커별로 카페 목록 분배
    tasks = []
    for cafe_url in cafe_urls:
        for w_idx, acc, drv in workers:
            nick = nickname_fn(acc) if nickname_fn else None
            tasks.append((w_idx, acc, drv, cafe_url, nick))

    _log(f"일괄 가입 시작: {len(tasks)}건 ({len(workers)}워커 × {len(cafe_urls)}카페)")

    def _task(w_idx, acc, drv, cafe_url, nick):
        w_log = lambda msg: _log(f"[워커#{w_idx+1}/{acc['id']}] {msg}")
        r = join_cafe(drv, cafe_url, nickname=nick, log_fn=w_log)
        return {
            "worker_idx": w_idx,
            "account_id": acc["id"],
            **r
        }

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(workers)) as pool:
        futures = {
            pool.submit(_task, w_idx, acc, drv, cafe_url, nick): (w_idx, cafe_url)
            for w_idx, acc, drv, cafe_url, nick in tasks
        }
        for f in concurrent.futures.as_completed(futures):
            try:
                results.append(f.result())
            except Exception as e:
                w_idx, cafe_url = futures[f]
                results.append({
                    "worker_idx": w_idx, "account_id": "", "cafe_url": cafe_url,
                    "ok": False, "msg": str(e)[:60], "error": "exception"
                })

    ok = sum(1 for r in results if r["ok"])
    _log(f"일괄 가입 완료: 성공 {ok}/{len(results)}")
    return results


# ═══════════════════════════════════════════════
# 내부 헬퍼 함수
# ═══════════════════════════════════════════════

def _extract_club_id(driver):
    """페이지에서 clubid 추출. 실패 시 None."""
    try:
        link = driver.find_element(By.CSS_SELECTOR, 'a[name="myCafeUrlLink"]')
        m = re.search(r'clubid=(\d+)', link.get_attribute("href") or "")
        if m:
            return m.group(1)
    except:
        pass
    try:
        m = re.search(r'clubid["\s:=]+(\d+)', driver.page_source[:10000])
        if m:
            return m.group(1)
    except:
        pass
    return None


def _navigate_to_join_page(driver, cafe_url, club_id, _log):
    """가입 페이지로 이동. 성공 시 True."""
    # 방법 1: JS joinCafe 호출
    try:
        driver.execute_script("joinCafe();")
        time.sleep(2)
        url, _ = func.get_page_safe(driver)
        if "JoinCafe" in url or "join" in url.lower():
            _log("가입 페이지 이동 (JS)")
            return True
    except:
        pass

    # 방법 2: 가입 버튼 클릭
    try:
        for btn in driver.find_elements(By.CSS_SELECTOR, "a, button"):
            txt = (btn.text or "").strip()
            if "카페 가입" in txt or "가입하기" in txt:
                btn.click()
                time.sleep(2)
                _log("가입 페이지 이동 (버튼 클릭)")
                return True
    except:
        pass

    # 방법 3: 직접 URL 이동
    if club_id:
        join_url = f"https://cafe.naver.com/CafeJoin.nhn?clubid={club_id}"
        driver.get(join_url)
        time.sleep(2)
        _log("가입 페이지 이동 (URL 직접)")
        return True

    # 방법 4: cafe_url에서 카페명 추출 후 URL 구성
    cafe_name = cafe_url.rstrip("/").split("/")[-1]
    if cafe_name:
        join_url = f"https://cafe.naver.com/{cafe_name}?iframe_url=/CafeJoin.nhn"
        driver.get(join_url)
        time.sleep(2)
        _log("가입 페이지 이동 (카페명 URL)")
        return True

    _log("가입 페이지 이동 실패")
    return False


def _fill_nickname(driver, nickname, _log):
    """닉네임 입력. nickname이 None이면 스킵 (기본 닉네임 사용)."""
    if not nickname:
        return
    try:
        # iframe 내부일 수 있으므로 전환 시도
        _switch_to_cafe_iframe(driver)

        nick_input = driver.find_elements(By.CSS_SELECTOR,
            "input[name='nickname'], input#nickname, input[placeholder*='별명'], input[placeholder*='닉네임']"
        )
        if nick_input:
            nick_input[0].clear()
            time.sleep(0.2)
            pyperclip.copy(nickname)
            nick_input[0].send_keys(Keys.CONTROL, "a")
            nick_input[0].send_keys(Keys.CONTROL, "v")
            _log(f"닉네임 입력: {nickname}")
            time.sleep(0.3)
    except Exception as e:
        _log(f"닉네임 입력 실패: {str(e)[:40]}")


def _handle_join_questions(driver, _log):
    """join_qna_area 기반 질문 처리 (선택형 + 서술형)"""
    try:
        _switch_to_cafe_iframe(driver)

        areas = driver.find_elements(By.CSS_SELECTOR, ".join_qna_area > div")
        if not areas:
            _log("가입 질문 없음")
            return

        _log(f"가입 질문 {len(areas)}개 발견")

        gemini_key = func.get_gemini_key()
        if not gemini_key:
            _log("Gemini API 키 없음 — 질문 답변 불가")
            return

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
                _log(f"[선택] Q: {q_text[:50]}...")
                _log(f"  선택지: {options}")

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
                _log(f"  → 선택: {options[idx] if idx < len(options) else idx}")
                time.sleep(0.3)
                continue

            # 서술형 (textarea / input)
            ta = area.find_elements(By.CSS_SELECTOR, "textarea, input[type='text']")
            if ta:
                if answer_attr:
                    answer = answer_attr.strip()
                    _log(f"[서술] Q: {q_text[:50]}... → answer 속성 사용")
                else:
                    prompt = (
                        f"네이버 카페 가입 질문에 답변해주세요.\n"
                        f"질문: {q_text}\n"
                        f"규칙: 자연스럽고 성의있는 한국어 1~2문장. 답변만 출력."
                    )
                    resp = model.generate_content(prompt)
                    answer = resp.text.strip()
                    _log(f"[서술] Q: {q_text[:50]}... → Gemini 생성")

                ta[0].click()
                time.sleep(0.2)
                pyperclip.copy(answer)
                ta[0].send_keys(Keys.CONTROL, "a")
                ta[0].send_keys(Keys.CONTROL, "v")
                _log(f"  → A: {answer[:50]}")
                time.sleep(0.3)

    except Exception as e:
        _log(f"가입 질문 처리 실패: {str(e)[:60]}")


def _solve_captcha(driver, _log, max_attempts=3):
    """캡차 이미지를 Gemini 2.5 Pro로 풀기. 최대 max_attempts회 시도."""
    try:
        _switch_to_cafe_iframe(driver)

        gemini_key = func.get_gemini_key()
        if not gemini_key:
            _log("Gemini API 키 없음 — 캡차 풀기 불가")
            return False

        genai.configure(api_key=gemini_key)
        model = genai.GenerativeModel("gemini-2.5-pro")

        for attempt in range(1, max_attempts + 1):
            _log(f"캡차 시도 {attempt}/{max_attempts}")

            # 재시도 시 새로고침 버튼 클릭
            if attempt > 1:
                try:
                    refresh_btn = driver.find_element(By.CSS_SELECTOR, ".join_captcha_info button .join_captcha_refresh")
                    refresh_btn.find_element(By.XPATH, "./ancestor::button").click()
                    _log("  캡차 새로고침...")
                    time.sleep(2)
                except:
                    _log("  새로고침 버튼 못 찾음")

            # 캡차 이미지 찾기
            img_el = driver.find_elements(By.CSS_SELECTOR, ".join_captcha_area img")
            if not img_el:
                _log("캡차 이미지 없음 — 스킵")
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
            _log(f"  캡차 인식: {captcha_text}")

            # 캡차 입력
            captcha_input = driver.find_element(By.CSS_SELECTOR, "#captcha")
            captcha_input.clear()
            time.sleep(0.2)
            captcha_input.send_keys(captcha_text)
            _log(f"  캡차 입력 완료")
            time.sleep(0.3)
            return True

        return False

    except Exception as e:
        _log(f"캡차 처리 실패: {str(e)[:60]}")
        return False


def _accept_terms(driver, _log):
    """가입 약관/동의 체크박스 모두 체크."""
    try:
        _switch_to_cafe_iframe(driver)
        checkboxes = driver.find_elements(By.CSS_SELECTOR,
            "input[type='checkbox'], .checkbox, label.check"
        )
        for cb in checkboxes:
            try:
                if not cb.is_selected():
                    cb.click()
                    time.sleep(0.2)
            except:
                try:
                    driver.execute_script("arguments[0].checked=true;arguments[0].dispatchEvent(new Event('change'));", cb)
                except:
                    pass
        if checkboxes:
            _log(f"약관 동의 {len(checkboxes)}개 체크")
    except Exception as e:
        _log(f"약관 동의 실패: {str(e)[:40]}")


def _click_join_button(driver, _log):
    """가입 완료 버튼 클릭. 성공 시 True."""
    try:
        _switch_to_cafe_iframe(driver)

        # 가입 버튼 탐색 (우선순위 순)
        selectors = [
            "a.btn_join, button.btn_join",
            "a.btn_submit, button.btn_submit",
            "input[type='submit']",
        ]
        for sel in selectors:
            btns = driver.find_elements(By.CSS_SELECTOR, sel)
            for btn in btns:
                txt = (btn.text or btn.get_attribute("value") or "").strip()
                if any(kw in txt for kw in ["가입", "완료", "신청", "확인"]):
                    btn.click()
                    _log(f"가입 버튼 클릭: {txt}")
                    return True

        # 폴백: 텍스트로 탐색
        for btn in driver.find_elements(By.CSS_SELECTOR, "a, button, input[type='submit'], input[type='button']"):
            txt = (btn.text or btn.get_attribute("value") or "").strip()
            if any(kw in txt for kw in ["카페 가입", "가입하기", "가입 완료", "가입 신청"]):
                btn.click()
                _log(f"가입 버튼 클릭: {txt}")
                return True

        _log("가입 버튼 못 찾음")
        return False

    except Exception as e:
        _log(f"가입 버튼 클릭 실패: {str(e)[:40]}")
        return False


def _switch_to_cafe_iframe(driver):
    """카페 iframe이 있으면 전환. 없으면 무시."""
    try:
        driver.switch_to.default_content()
        iframes = driver.find_elements(By.CSS_SELECTOR, "iframe#cafe_main, iframe[name='cafe_main']")
        if iframes:
            driver.switch_to.frame(iframes[0])
    except:
        pass


def _extract_error_message(driver):
    """페이지에서 에러 메시지 추출."""
    try:
        for sel in [".error_message", ".alert_message", ".message", ".err_msg"]:
            els = driver.find_elements(By.CSS_SELECTOR, sel)
            for el in els:
                txt = el.text.strip()
                if txt:
                    return txt
    except:
        pass
    return None


# ═══════════════════════════════════════════════
# 가입 결과 구글시트 기록
# ═══════════════════════════════════════════════

def save_results_to_gsheet(results, sheet_name="가입결과", log_fn=None):
    """
    가입 결과를 구글시트에 기록한다.

    Args:
        results: batch_join_cafes 반환값 또는 동일 형식의 dict 리스트
            [{"worker_idx", "account_id", "cafe_url", "ok", "msg", "error"}, ...]
        sheet_name: 기록할 시트(탭) 이름 (기본: "가입결과")
        log_fn: 로그 콜백

    Returns:
        bool: 기록 성공 여부
    """
    from datetime import datetime
    _log = log_fn or (lambda msg: logger.info(msg))

    rows = []
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for r in results:
        rows.append([
            ts,
            r.get("account_id", ""),
            r.get("cafe_url", ""),
            "성공" if r.get("ok") else "실패",
            r.get("msg", ""),
            r.get("error", "") or "",
        ])

    return func.append_to_gsheet(rows, sheet_name=sheet_name, log_fn=_log)
