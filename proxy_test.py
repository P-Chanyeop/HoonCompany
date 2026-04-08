"""
프록시 & 워커 테스트 스크립트 (Selenium)
- 1단계: 프록시 100개 연결 상태 전수 검증
- 2단계: 워커 50개 동시 실행 테스트
- 3단계: 네이버 접속 테스트

사용법:
  python proxy_test.py proxies.txt
  python proxy_test.py proxies.txt --workers 10
  python proxy_test.py proxies.txt --step 1
  python proxy_test.py proxies.txt --headless off   # 브라우저 보이게
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

IP_CHECK_URL = "https://httpbin.org/ip"
NAVER_CAFE_URL = "https://cafe.naver.com"
TIMEOUT = 15


def load_proxies(filepath):
    proxies = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                proxies.append(line)
    return proxies


def create_driver(proxy_str=None, headless=True):
    opts = Options()
    if headless:
        opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
    if proxy_str:
        parts = proxy_str.split(":")
        if len(parts) == 4:
            ip, port, user, pw = parts
            opts.add_argument(f"--proxy-server=http://{ip}:{port}")
            # 인증 프록시는 extension으로 처리
            ext = _create_proxy_auth_extension(ip, port, user, pw)
            opts.add_extension(ext)
        elif len(parts) == 2:
            opts.add_argument(f"--proxy-server=http://{proxy_str}")
    driver = webdriver.Chrome(options=opts)
    driver.set_page_load_timeout(TIMEOUT)
    driver.implicitly_wait(5)
    return driver


def _create_proxy_auth_extension(host, port, user, pw):
    """인증 프록시용 Chrome 확장 생성."""
    import zipfile
    import tempfile

    manifest = json.dumps({
        "version": "1.0.0", "manifest_version": 2,
        "name": "Proxy Auth", "permissions": ["proxy", "tabs", "unlimitedStorage",
                                                "storage", "<all_urls>", "webRequest",
                                                "webRequestBlocking"],
        "background": {"scripts": ["background.js"]},
    })
    background = """
    var config = {
        mode: "fixed_servers",
        rules: { singleProxy: { scheme: "http", host: "%s", port: parseInt(%s) }, bypassList: [] }
    };
    chrome.proxy.settings.set({value: config, scope: "regular"}, function(){});
    function callbackFn(details) {
        return { authCredentials: { username: "%s", password: "%s" } };
    }
    chrome.webRequest.onAuthRequired.addListener(callbackFn, {urls:["<all_urls>"]}, ['blocking']);
    """ % (host, port, user, pw)

    tmpfile = tempfile.NamedTemporaryFile(suffix=".zip", delete=False)
    with zipfile.ZipFile(tmpfile, "w") as zp:
        zp.writestr("manifest.json", manifest)
        zp.writestr("background.js", background)
    return tmpfile.name


def log(msg, level="INFO"):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {level} — {msg}")


# ═══════════════════════════════════════════════
# 1단계: 프록시 전수 검증
# ═══════════════════════════════════════════════

def test_single_proxy(idx, proxy_str, headless):
    driver = None
    try:
        start = time.time()
        driver = create_driver(proxy_str, headless)
        driver.get(IP_CHECK_URL)
        ms = int((time.time() - start) * 1000)
        body = driver.find_element(By.TAG_NAME, "body").text
        ip = json.loads(body).get("origin", "?")
        return {"idx": idx, "proxy": proxy_str, "ok": True, "ip": ip, "ms": ms, "error": None}
    except Exception as e:
        return {"idx": idx, "proxy": proxy_str, "ok": False, "ip": None, "ms": 0, "error": str(e)[:80]}
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass


def step1_verify_all(proxies, headless):
    log(f"=== 1단계: 프록시 전수 검증 ({len(proxies)}개) ===")
    results = []

    # 동시 10개씩 (브라우저 리소스 고려)
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
        futures = {pool.submit(test_single_proxy, i, p, headless): i for i, p in enumerate(proxies)}
        for future in concurrent.futures.as_completed(futures):
            r = future.result()
            results.append(r)
            status = "✅" if r["ok"] else "❌"
            detail = f"IP={r['ip']} ({r['ms']}ms)" if r["ok"] else r["error"]
            print(f"  [{r['idx']+1:3d}] {status} {r['proxy'][:30]:30s} → {detail}")

    results.sort(key=lambda x: x["idx"])
    ok = [r for r in results if r["ok"]]
    fail = [r for r in results if not r["ok"]]

    ips = [r["ip"] for r in ok]
    dupes = len(ips) - len(set(ips))

    log(f"결과: 성공 {len(ok)}개 / 실패 {len(fail)}개 / 중복IP {dupes}개")
    if fail:
        log(f"실패 목록:", "WARN")
        for r in fail:
            print(f"    ❌ {r['proxy']} — {r['error']}")
    if dupes > 0:
        log(f"⚠️  중복 IP {dupes}개 — 같은 IP 워커는 차단 위험", "WARN")

    return ok, fail


# ═══════════════════════════════════════════════
# 2단계: 워커 N개 동시 실행
# ═══════════════════════════════════════════════

def worker_task(worker_id, proxy_str, headless):
    driver = None
    try:
        start = time.time()
        driver = create_driver(proxy_str, headless)
        driver.get(IP_CHECK_URL)
        ms = int((time.time() - start) * 1000)
        body = driver.find_element(By.TAG_NAME, "body").text
        ip = json.loads(body).get("origin", "?")
        return {"worker": worker_id, "ok": True, "ip": ip, "ms": ms, "error": None}
    except Exception as e:
        return {"worker": worker_id, "ok": False, "ip": None, "ms": 0, "error": str(e)[:80]}
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass


def step2_concurrent_workers(proxies, worker_count, headless):
    log(f"=== 2단계: 워커 {worker_count}개 동시 실행 테스트 ===")
    selected = proxies[:worker_count]

    start_all = time.time()
    results = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=worker_count) as pool:
        futures = {pool.submit(worker_task, i, p, headless): i for i, p in enumerate(selected)}
        for future in concurrent.futures.as_completed(futures):
            r = future.result()
            results.append(r)
            status = "✅" if r["ok"] else "❌"
            detail = f"IP={r['ip']} ({r['ms']}ms)" if r["ok"] else r["error"]
            print(f"  워커#{r['worker']+1:2d} {status} {detail}")

    total_ms = int((time.time() - start_all) * 1000)
    ok = [r for r in results if r["ok"]]
    fail = [r for r in results if not r["ok"]]
    avg_ms = sum(r["ms"] for r in ok) // max(len(ok), 1)

    log(f"결과: 성공 {len(ok)}/{worker_count} | 실패 {len(fail)} | 평균 {avg_ms}ms | 총 {total_ms}ms")
    return ok, fail


# ═══════════════════════════════════════════════
# 3단계: 네이버 접속 테스트
# ═══════════════════════════════════════════════

def naver_task(worker_id, proxy_str, headless):
    driver = None
    try:
        start = time.time()
        driver = create_driver(proxy_str, headless)
        driver.get(NAVER_CAFE_URL)
        ms = int((time.time() - start) * 1000)
        title = driver.title
        page = driver.page_source[:3000].lower()
        blocked = "captcha" in page or "차단" in page or "비정상" in page
        is_ok = "카페" in title or "cafe" in title.lower()
        return {"worker": worker_id, "ok": is_ok and not blocked, "title": title[:40],
                "ms": ms, "blocked": blocked, "error": None}
    except Exception as e:
        return {"worker": worker_id, "ok": False, "title": "", "ms": 0, "blocked": False,
                "error": str(e)[:80]}
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass


def step3_naver_test(proxies, worker_count, headless):
    log(f"=== 3단계: 네이버 카페 접속 테스트 (워커 {worker_count}개) ===")
    selected = proxies[:worker_count]
    results = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=worker_count) as pool:
        futures = {pool.submit(naver_task, i, p, headless): i for i, p in enumerate(selected)}
        for future in concurrent.futures.as_completed(futures):
            r = future.result()
            results.append(r)
            if r["ok"]:
                print(f"  워커#{r['worker']+1:2d} ✅ {r['title']} ({r['ms']}ms)")
            elif r["blocked"]:
                print(f"  워커#{r['worker']+1:2d} 🚫 차단/캡차 ({r['ms']}ms)")
            else:
                print(f"  워커#{r['worker']+1:2d} ❌ {r['error']}")

    ok = [r for r in results if r["ok"]]
    blocked = [r for r in results if r["blocked"]]
    fail = [r for r in results if not r["ok"] and not r["blocked"]]

    log(f"결과: 정상 {len(ok)} | 차단 {len(blocked)} | 실패 {len(fail)} / 총 {worker_count}개")


# ═══════════════════════════════════════════════
# 메인
# ═══════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="프록시 & 워커 테스트 (Selenium)")
    parser.add_argument("proxy_file", help="프록시 파일 경로")
    parser.add_argument("--workers", type=int, default=50, help="워커 수 (기본: 50)")
    parser.add_argument("--step", type=int, default=0, help="특정 단계만 (1/2/3, 0=전체)")
    parser.add_argument("--headless", default="on", choices=["on", "off"], help="헤드리스 모드 (기본: on)")
    args = parser.parse_args()

    if not os.path.isfile(args.proxy_file):
        print(f"❌ 파일 없음: {args.proxy_file}")
        sys.exit(1)

    headless = args.headless == "on"
    proxies = load_proxies(args.proxy_file)
    log(f"프록시 {len(proxies)}개 로드 완료")

    if len(proxies) < args.workers:
        log(f"⚠️  프록시({len(proxies)}개) < 워커({args.workers}개)", "WARN")

    live_proxies = [p for p in proxies]

    if args.step in (0, 1):
        ok, fail = step1_verify_all(proxies, headless)
        live_proxies = [r["proxy"] for r in ok]
        print()

    if args.step in (0, 2):
        count = min(args.workers, len(live_proxies))
        if count < args.workers:
            log(f"살아있는 프록시 {count}개로 테스트", "WARN")
        step2_concurrent_workers(live_proxies, count, headless)
        print()

    if args.step in (0, 3):
        count = min(args.workers, len(live_proxies))
        step3_naver_test(live_proxies, count, headless)
        print()

    log("테스트 완료")


if __name__ == "__main__":
    main()
