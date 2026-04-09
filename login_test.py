"""
네이버 로그인 테스트 스크립트 (Selenium)
- 계정 + 프록시 1:1 매핑
- 로그인 성공/실패 확인

사용법:
  python login_test.py 네이버id.txt proxies.txt
  python login_test.py 네이버id.txt proxies.txt --workers 5
  python login_test.py 네이버id.txt proxies.txt --workers 1   # 1개만 테스트
"""

import sys
import os
import time
import json
import argparse
import concurrent.futures
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

try:
    import undetected_chromedriver as uc
    USE_UC = True
except ImportError:
    USE_UC = False
import pyperclip


LOGIN_URL = "https://nid.naver.com/nidlogin.login"
TIMEOUT = 20


def load_accounts(filepath):
    """계정 파일 로드. TAB 또는 : 구분."""
    accounts = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "\t" in line:
                parts = line.split("\t", 1)
            else:
                parts = line.split(":", 1)
            if len(parts) == 2:
                accounts.append({"id": parts[0].strip(), "pw": parts[1].strip()})
    return accounts


def load_proxies(filepath):
    proxies = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                proxies.append(line)
    return proxies


def create_driver(proxy_str=None):
    opts = Options()
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)
    opts.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
    if proxy_str:
        opts.add_argument(f"--proxy-server={proxy_str}")
    driver = webdriver.Chrome(options=opts)
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    })
    driver.set_page_load_timeout(TIMEOUT)
    driver.implicitly_wait(5)
    return driver


def log(msg, level="INFO"):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {level} — {msg}")


def login_worker(worker_id, account, proxy_str):
    """워커 1개: 프록시로 네이버 로그인 시도."""
    driver = None
    nid = account["id"]
    try:
        driver = create_driver(proxy_str)
        driver.get(LOGIN_URL)
        time.sleep(2)

        # 클립보드 붙여넣기 방식 (send_keys 미사용)
        id_input = driver.find_element(By.CSS_SELECTOR, "#id")
        id_input.click()
        time.sleep(0.3)
        id = account["id"]
        pyperclip.copy(id)
        id_input.send_keys(Keys.CONTROL, "v")
        time.sleep(0.3)
        
        # 비밀번호 입력
        pw = account["pw"]
        pyperclip.copy(pw)
        pw_input = driver.find_element(By.CSS_SELECTOR, "#pw")
        pw_input.click()
        time.sleep(0.3)
        pw_input.send_keys(Keys.CONTROL, "v")
        time.sleep(0.3)

        # 로그인 버튼 클릭
        login_btn = driver.find_element(By.CSS_SELECTOR, ".btn_login, #log\\.login, .btn_global")
        login_btn.click()
        time.sleep(3)

        url = driver.current_url
        title = driver.title

        # 결과 판정
        if "nid.naver.com" not in url and "nidlogin" not in url:
            return {"worker": worker_id, "id": nid, "ok": True,
                    "msg": f"로그인 성공 → {url[:50]}", "error": None}
        elif "captcha" in url or "캡차" in driver.page_source[:2000]:
            return {"worker": worker_id, "id": nid, "ok": False,
                    "msg": "캡차 발생", "error": "captcha"}
        elif "보안" in driver.page_source[:2000] or "기기" in driver.page_source[:2000]:
            return {"worker": worker_id, "id": nid, "ok": False,
                    "msg": "보안 인증 필요 (새 기기)", "error": "security"}
        else:
            return {"worker": worker_id, "id": nid, "ok": False,
                    "msg": f"로그인 실패 (URL: {url[:60]})", "error": "login_fail"}

    except Exception as e:
        return {"worker": worker_id, "id": nid, "ok": False,
                "msg": str(e)[:80], "error": "exception"}
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass


def main():
    parser = argparse.ArgumentParser(description="네이버 로그인 테스트")
    parser.add_argument("account_file", help="계정 파일 (ID:PW 또는 ID\\tPW)")
    parser.add_argument("proxy_file", help="프록시 파일")
    parser.add_argument("--workers", type=int, default=5, help="동시 워커 수 (기본: 5)")
    args = parser.parse_args()

    accounts = load_accounts(args.account_file)
    proxies = load_proxies(args.proxy_file)

    log(f"계정 {len(accounts)}개 / 프록시 {len(proxies)}개 로드")

    count = min(args.workers, len(accounts), len(proxies))
    log(f"=== 네이버 로그인 테스트 (워커 {count}개) ===")

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=count) as pool:
        futures = {
            pool.submit(login_worker, i, accounts[i], proxies[i]): i
            for i in range(count)
        }
        for future in concurrent.futures.as_completed(futures):
            r = future.result()
            results.append(r)
            status = "✅" if r["ok"] else "❌"
            print(f"  워커#{r['worker']+1:2d} {status} [{r['id']}] {r['msg']}")

    ok = [r for r in results if r["ok"]]
    captcha = [r for r in results if r.get("error") == "captcha"]
    security = [r for r in results if r.get("error") == "security"]
    fail = [r for r in results if not r["ok"] and r.get("error") not in ("captcha", "security")]

    print()
    log(f"결과: 성공 {len(ok)} | 캡차 {len(captcha)} | 보안인증 {len(security)} | 실패 {len(fail)} / 총 {count}개")


if __name__ == "__main__":
    main()
