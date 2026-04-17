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
import os
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
        # 이미 카페 페이지에 있으면 재접속 안 함
        current = driver.current_url or ""
        cafe_short = cafe_url.rstrip("/").split("/")[-1]
        if cafe_short not in current:
            driver.get(cafe_url)
            time.sleep(1)
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

        time.sleep(1)
        url, page = func.get_page_safe(driver)

        # 비공개 카페 체크
        if "비공개" in page or "멤버만" in page:
            _log("비공개 카페 — 가입 불가")
            return {**result_base, "ok": False, "msg": "비공개 카페", "error": "private_cafe"}

        # 3) 닉네임 입력
        _fill_nickname(driver, nickname, _log)

        # 4) 가입 질문 처리 (있는 경우)
        _handle_join_questions(driver, _log)

        # 5~7) 캡차 + 약관 + 가입 버튼 (최대 3회 재시도)
        for captcha_try in range(3):
            captcha_ok = _solve_captcha(driver, _log, max_attempts=3)
            if not captcha_ok:
                _log(f"캡차 인식 실패 ({captcha_try+1}/3)")
                # 새로고침
                try:
                    _switch_to_cafe_iframe(driver)
                    refresh_btn = driver.find_elements(By.CSS_SELECTOR, "button:has(.join_captcha_refresh), .join_captcha_info button")
                    if refresh_btn:
                        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", refresh_btn[0])
                        refresh_btn[0].click()
                        time.sleep(1)
                    driver.switch_to.default_content()
                except:
                    pass
                continue
            _accept_terms(driver, _log)

            if not _click_join_button(driver, _log):
                return {**result_base, "ok": False, "msg": "가입 버튼 클릭 실패", "error": "join_failed"}

            time.sleep(1.5)
            # 팝업 차단 등 alert 처리
            for _ in range(3):
                try:
                    from selenium.webdriver.common.alert import Alert as _Alert
                    alert = _Alert(driver)
                    _log(f"alert 감지: {alert.text[:40]}")
                    alert.accept()
                    time.sleep(0.5)
                except:
                    break

            # 팝업 창(새 탭/윈도우) 닫기 — 원래 탭만 남기기
            main_handle = driver.window_handles[0]
            if len(driver.window_handles) > 1:
                for handle in driver.window_handles[1:]:
                    try:
                        driver.switch_to.window(handle)
                        _log(f"팝업 창 닫기: {driver.title[:30]}")
                        driver.close()
                    except:
                        pass
                driver.switch_to.window(main_handle)

            # iframe 안에서 캡차 에러 체크 (페이지 이동 전)
            captcha_failed = False
            try:
                _switch_to_cafe_iframe(driver)
                err_label = driver.find_elements(By.CSS_SELECTOR, "label[for='captcha']")
                if err_label and ("잘못" in err_label[0].text or "자동 가입 방지" in err_label[0].text):
                    captcha_failed = True
                driver.switch_to.default_content()
            except:
                try:
                    driver.switch_to.default_content()
                except:
                    pass

            if captcha_failed:
                _log(f"캡차 틀림 ({captcha_try+1}/3) — 재시도")
                try:
                    _switch_to_cafe_iframe(driver)
                    refresh_btn = driver.find_elements(By.CSS_SELECTOR, ".join_captcha_info button")
                    if refresh_btn:
                        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", refresh_btn[0])
                        refresh_btn[0].click()
                        time.sleep(1)
                    driver.switch_to.default_content()
                except:
                    pass
                continue

            # 페이지 이동 확인
            post_url = driver.current_url
            url2, page2 = func.get_page_safe(driver)

            if "가입을 축하" in page2 or "가입이 완료" in page2 or "가입 완료" in page2:
                _log("카페 가입 성공!")
                return {**result_base, "ok": True, "msg": "가입 성공", "error": None}

            if "승인" in page2 or "가입 신청" in page2:
                _log("가입 신청 완료 (승인 대기)")
                return {**result_base, "ok": True, "msg": "가입 신청 완료 (승인 대기)", "error": None}

            if "이미 가입" in page2 or "이미 회원" in page2:
                _log("이미 가입된 카페")
                return {**result_base, "ok": True, "msg": "이미 가입된 카페", "error": "already_member"}

            cafe_short = cafe_url.rstrip("/").split("/")[-1]
            if cafe_short in post_url and "join" not in post_url.lower():
                _log("카페 메인으로 이동 — 가입 성공")
                return {**result_base, "ok": True, "msg": "가입 성공 (리다이렉트)", "error": None}

            # 결과 불명 → 카페 재접속해서 가입 확인
            _log("가입 결과 불명 — 카페 재접속하여 가입 확인")
            driver.get(cafe_url)
            time.sleep(1)
            func.dismiss_alert(driver)
            recheck = check_membership(driver, cafe_url, _log)
            if recheck.get("is_member"):
                _log("카페 재확인 — 가입 성공!")
                return {**result_base, "ok": True, "msg": "가입 성공 (재확인)", "error": None}

            _log(f"가입 결과 불명: {post_url[:60]}")
            return {**result_base, "ok": False, "msg": f"가입 결과 불명 ({post_url[:50]})", "error": "join_failed"}

        _log("캡차 3회 실패 — 가입 실패")
        return {**result_base, "ok": False, "msg": "캡차 3회 실패", "error": "captcha"}

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
        time.sleep(1)
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
                time.sleep(1)
                _log("가입 페이지 이동 (버튼 클릭)")
                return True
    except:
        pass

    # 방법 3: 직접 URL 이동
    if club_id:
        join_url = f"https://cafe.naver.com/CafeJoin.nhn?clubid={club_id}"
        driver.get(join_url)
        time.sleep(1)
        _log("가입 페이지 이동 (URL 직접)")
        return True

    # 방법 4: cafe_url에서 카페명 추출 후 URL 구성
    cafe_name = cafe_url.rstrip("/").split("/")[-1]
    if cafe_name:
        join_url = f"https://cafe.naver.com/{cafe_name}?iframe_url=/CafeJoin.nhn"
        driver.get(join_url)
        time.sleep(1)
        _log("가입 페이지 이동 (카페명 URL)")
        return True

    _log("가입 페이지 이동 실패")
    return False


def _fill_nickname(driver, nickname, _log):
    """닉네임 입력. 중복이면 랜덤 숫자 붙여서 재시도."""
    try:
        _switch_to_cafe_iframe(driver)

        nick_input = driver.find_elements(By.CSS_SELECTOR,
            "input[name='nickname'], input#nickname, input[placeholder*='별명'], input[placeholder*='닉네임']"
        )
        if not nick_input:
            _log("닉네임 입력 영역 없음 — 스킵")
            return

        import random as _rand

        # 닉네임이 없으면 한글 랜덤 생성 (숫자 없이 순수 한글만)
        if not nickname:
            _adj = [
                "행복한","귀여운","맑은","따뜻한","빛나는","즐거운","상큼한","포근한","활기찬","싱그러운",
                "달콤한","소중한","반짝이는","사랑스런","건강한","설레는","편안한","든든한","깜찍한","고운",
                "푸른","밝은","착한","예쁜","멋진","씩씩한","용감한","지혜로운","넉넉한","다정한",
                "기운찬","산뜻한","화사한","청량한","아늑한","정겨운","유쾌한","명랑한","온화한","단아한",
                "영롱한","찬란한","눈부신","향기로운","그윽한","잔잔한","평화로운","자유로운","순수한","청초한",
                "기특한","야무진","당찬","늠름한","의젓한","듬직한","알뜰한","꼼꼼한","슬기로운","재빠른",
            ]
            _noun = [
                "하늘","바다","구름","별빛","햇살","나비","토끼","고양이","다람쥐","꽃잎",
                "민들레","수달","참새","여우","강아지","해바라기","무지개","은하수","달빛","새벽",
                "노을","산들바람","이슬","동백","목련","라일락","벚꽃","진달래","개나리","코스모스",
                "소나무","단풍","은행잎","클로버","풀잎","연꽃","장미","튤립","수선화","안개꽃",
                "호수","시냇물","폭포","오솔길","들판","초원","숲속","언덕","봄날","여름밤",
                "가을빛","겨울별","아침","저녁놀","보름달","샛별","미르","도담","가온","나래",
            ]
            nickname = _rand.choice(_adj) + _rand.choice(_noun)
        base_nick = nickname

        for try_i in range(5):
            current_nick = base_nick if try_i == 0 else _rand.choice(_adj) + _rand.choice(_noun)
            nick_input[0].clear()
            time.sleep(0.1)
            nick_input[0].send_keys(current_nick)
            nick_input[0].send_keys(Keys.TAB)  # 포커스 이동 → 중복 체크 트리거
            time.sleep(1)

            # 중복 체크 결과 확인
            err_els = driver.find_elements(By.CSS_SELECTOR, ".error_msg, .nick_error, span.error, p.error")
            page_text = driver.page_source[:3000]
            if "이미 사용 중" in page_text or "사용할 수 없는" in page_text:
                _log(f"닉네임 중복: {current_nick} ({try_i+1}/5)")
                continue
            if "사용할 수 있는" in page_text:
                _log(f"닉네임 사용 가능: {current_nick}")
                return
            # 판별 불가면 그냥 진행
            _log(f"닉네임 입력: {current_nick}")
            return

        _log("닉네임 5회 시도 실패 — 마지막 값으로 진행")
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
    """2Captcha API로 캡차 풀기."""
    for attempt in range(1, max_attempts + 1):
        try:
            _log(f"캡차 시도 {attempt}/{max_attempts}")

            # 매 시도마다 iframe 재전환
            try:
                driver.switch_to.default_content()
            except:
                pass
            _switch_to_cafe_iframe(driver)
            _log("  iframe 전환 완료")

            if attempt > 1:
                try:
                    refresh_btn = driver.find_elements(By.CSS_SELECTOR, ".join_captcha_info button, button.btn")
                    for rb in refresh_btn:
                        try:
                            if "새로고침" in (rb.text or "") or rb.find_elements(By.CSS_SELECTOR, ".join_captcha_refresh"):
                                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", rb)
                                rb.click()
                                _log("  캡차 새로고침...")
                                time.sleep(1)
                                break
                        except:
                            continue
                except:
                    _log("  새로고침 버튼 못 찾음")

            _log("  캡차 이미지 탐색...")
            img_el = driver.find_elements(By.CSS_SELECTOR, ".join_captcha_area img")
            _log(f"  iframe 안 이미지: {len(img_el)}개")
            if not img_el:
                time.sleep(2)
                img_el = driver.find_elements(By.CSS_SELECTOR, ".join_captcha_area img")
                _log(f"  2초 대기 후 이미지: {len(img_el)}개")
            if not img_el:
                try:
                    driver.switch_to.default_content()
                    img_el = driver.find_elements(By.CSS_SELECTOR, ".join_captcha_area img, #captchaimg, img[src*='captcha']")
                    _log(f"  iframe 밖 이미지: {len(img_el)}개")
                    if not img_el:
                        _switch_to_cafe_iframe(driver)
                except:
                    pass
            if not img_el:
                _log("  캡차 이미지 없음 — 스킵")
                return True

            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", img_el[0])
            time.sleep(0.3)

            # 이미지 다운로드
            import tempfile, urllib.request
            img_src = img_el[0].get_attribute("src") or ""
            tmp_path = None
            img_data = None
            _log(f"  캡차 이미지 src: {img_src[:80]}")

            if img_src.startswith("http"):
                try:
                    fd, tmp_path = tempfile.mkstemp(suffix=".png")
                    os.close(fd)
                    urllib.request.urlretrieve(img_src, tmp_path)
                    with open(tmp_path, "rb") as f:
                        img_data = f.read()
                    _log(f"  캡차 이미지 다운로드 성공: {len(img_data)}bytes")
                except Exception as dl_err:
                    _log(f"  캡차 이미지 다운로드 실패: {str(dl_err)[:40]}")
                    img_data = None
            else:
                _log(f"  캡차 이미지 src가 http가 아님 — 스크린샷 시도")

            if not img_data:
                try:
                    img_b64 = img_el[0].screenshot_as_base64
                    img_data = base64.b64decode(img_b64)
                    _log(f"  캡차 스크린샷 성공: {len(img_data)}bytes")
                except Exception as ss_err:
                    _log(f"  캡차 스크린샷 실패: {str(ss_err)[:40]}")
                    continue

            if not img_data:
                _log(f"  이미지 데이터 없음 ({attempt}/{max_attempts})")
                continue

            # 2Captcha로 풀기
            captcha_text = _solve_with_2captcha(img_data, _log)

            # 임시 파일 삭제
            if tmp_path and os.path.isfile(tmp_path):
                try:
                    os.remove(tmp_path)
                except:
                    pass

            if not captcha_text:
                _log(f"  캡차 인식 실패 ({attempt}/{max_attempts})")
                continue

            # 캡차 입력
            captcha_inputs = driver.find_elements(By.CSS_SELECTOR, "#captcha, input[name='captcha']")
            if not captcha_inputs:
                # iframe 전환 재시도
                try:
                    driver.switch_to.default_content()
                except:
                    pass
                _switch_to_cafe_iframe(driver)
                captcha_inputs = driver.find_elements(By.CSS_SELECTOR, "#captcha, input[name='captcha']")
            if not captcha_inputs:
                _log(f"  캡차 입력 영역 못 찾음 ({attempt}/{max_attempts})")
                continue
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", captcha_inputs[0])
            captcha_inputs[0].clear()
            time.sleep(0.1)
            captcha_inputs[0].send_keys(captcha_text)
            _log(f"  캡차 입력 완료: {captcha_text}")
            time.sleep(0.2)
            return True

        except Exception as e:
            _log(f"  캡차 처리 에러 ({attempt}/{max_attempts}): {str(e)[:60]}")
            continue

    return False


def _solve_with_2captcha(img_data, _log):
    """2Captcha API로 이미지 캡차 풀기."""
    import json, urllib.request, urllib.parse
    api_key = func.get_2captcha_key()
    if not api_key:
        _log("  2Captcha API 키 없음 — 스킵")
        return None

    try:
        # 1) 캡차 제출
        img_b64 = base64.b64encode(img_data).decode()
        payload = urllib.parse.urlencode({
            "key": api_key,
            "method": "base64",
            "body": img_b64,
            "json": 1,
        }).encode()
        req = urllib.request.Request("http://2captcha.com/in.php", data=payload)
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode())

        if result.get("status") != 1:
            _log(f"  2Captcha 제출 실패: {result.get('request', '')}")
            return None

        task_id = result["request"]
        _log(f"  2Captcha 제출 완료: task_id={task_id}")

        # 2) 결과 폴링 (최대 60초)
        for _ in range(12):
            time.sleep(5)
            poll_url = f"http://2captcha.com/res.php?key={api_key}&action=get&id={task_id}&json=1"
            with urllib.request.urlopen(poll_url, timeout=10) as resp2:
                result2 = json.loads(resp2.read().decode())

            if result2.get("status") == 1:
                answer = result2["request"]
                _log(f"  2Captcha 인식: {answer}")
                return answer
            elif result2.get("request") == "CAPCHA_NOT_READY":
                continue
            else:
                _log(f"  2Captcha 에러: {result2.get('request', '')}")
                return None

        _log("  2Captcha 타임아웃")
        return None

    except Exception as e:
        _log(f"  2Captcha 실패: {str(e)[:40]}")
        return None


def _accept_terms(driver, _log):
    """가입 약관/동의 체크박스 모두 체크."""
    try:
        _switch_to_cafe_iframe(driver)
        checkboxes = driver.find_elements(By.CSS_SELECTOR,
            "input[type='checkbox'], .checkbox, label.check"
        )
        for cb in checkboxes:
            try:
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", cb)
                if not cb.is_selected():
                    cb.click()
                    time.sleep(0.1)
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

        selectors = [
            "a.btn_join, button.btn_join",
            "a.btn_submit, button.btn_submit",
            "input[type='submit']",
        ]
        for sel in selectors:
            btns = driver.find_elements(By.CSS_SELECTOR, sel)
            for btn in btns:
                txt = (btn.text or btn.get_attribute("value") or "").strip()
                if any(kw in txt for kw in ["가입", "완료", "신청", "확인", "동의"]):
                    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
                    btn.click()
                    _log(f"가입 버튼 클릭: {txt}")
                    return True

        for btn in driver.find_elements(By.CSS_SELECTOR, "a, button, input[type='submit'], input[type='button']"):
            txt = (btn.text or btn.get_attribute("value") or "").strip()
            if any(kw in txt for kw in ["카페 가입", "가입하기", "가입 완료", "가입 신청", "동의 후 가입"]):
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
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
