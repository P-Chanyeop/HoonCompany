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

from PIL import Image as PILImage

import undetected_chromedriver as uc
# from selenium import webdriver
# from selenium.webdriver.chrome.options import Options
# from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.alert import Alert
import pyperclip
import google.generativeai as genai

import threading

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s — %(message)s")
logger = logging.getLogger(__name__)

# 클립보드 동시 접근 방지 (병렬 워커에서 pyperclip 사용 시)
_clipboard_lock = threading.Lock()

def _get_base_dir():
    """EXE 실행 시 EXE가 있는 폴더, 스크립트 실행 시 스크립트 폴더."""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

CONFIG_PATH = os.path.join(_get_base_dir(), "config.ini")


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


def get_2captcha_key():
    cfg = load_config()
    return cfg.get("2captcha", "api_key", fallback="").strip()


# ═══════════════════════════════════════════════
# 구글시트에서 계정 로드
# ═══════════════════════════════════════════════

def load_accounts_from_gsheet():
    """구글시트에서 계정 로드 (A:아이디, B:비밀번호, C:성함, D:생년월일, E:성별)"""
    cfg = load_config()
    gs_id = cfg.get("google_sheets", "sheet_id", fallback="")
    if not gs_id:
        raise Exception("config.ini에 구글시트 ID(sheet_id)가 설정되지 않았습니다.")
    try:
        service = _get_sheets_service_write()
        if not service:
            raise Exception("구글시트 인증 실패 — credentials.json 또는 token.json을 확인하세요.")
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
        raise


def group_accounts_by_id(accounts):
    """같은 아이디를 그룹핑. 반환: [{id, pw, name, ..., tasks: [{cafe_url, menu_id, post_count}, ...]}, ...]"""
    from collections import OrderedDict
    groups = OrderedDict()
    for acc in accounts:
        nid = acc["id"]
        if nid not in groups:
            groups[nid] = {
                "id": acc["id"],
                "pw": acc["pw"],
                "name": acc.get("name", ""),
                "birth": acc.get("birth", ""),
                "gender": acc.get("gender", ""),
                "tasks": [],
            }
        groups[nid]["tasks"].append({
            "cafe_url": acc.get("cafe_url", ""),
            "menu_id": acc.get("menu_id", ""),
            "post_count": acc.get("post_count", 1),
        })
    result = list(groups.values())
    logger.info(f"아이디 그룹핑: {len(accounts)}행 → {len(result)}개 워커")
    return result


# ═══════════════════════════════════════════════
# 구글시트 쓰기
# ═══════════════════════════════════════════════

def _get_sheets_service_write():
    """쓰기 가능한 구글시트 서비스 반환. 서비스 계정 인증."""
    from google.oauth2.service_account import Credentials
    from googleapiclient.discovery import build

    SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
    cfg = load_config()
    sa_file = cfg.get("google_sheets", "sa_file", fallback="")

    # sa_file이 설정되어 있으면 그 경로, 아니면 기본 credentials.json
    if sa_file and os.path.isfile(sa_file):
        sa_path = sa_file
    else:
        sa_path = os.path.join(_get_base_dir(), "credentials.json")

    if not os.path.isfile(sa_path):
        raise Exception(f"서비스 계정 키 파일이 없습니다: {sa_path}")

    creds = Credentials.from_service_account_file(sa_path, scopes=SCOPES)
    return build('sheets', 'v4', credentials=creds)


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


def append_to_gsheet_with_color(rows, sheet_name="결과값", log_fn=None):
    """
    구글시트에 행 추가 + 성공/실패에 따라 배경색 적용.
    성공: #d9ead2 (연두), 실패: #f4cccc (연빨강)
    rows: [[col1, ..., col12(status), col13(error)], ...]
    status 컬럼(인덱스 11)이 "성공"이면 연두, 아니면 연빨강.
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
            return False

        # 1) 행 추가
        service.spreadsheets().values().append(
            spreadsheetId=gs_id,
            range=f"{sheet_name}!A1",
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body={"values": rows}
        ).execute()

        # 2) 추가된 행 위치 파악 (현재 데이터 행 수)
        result = service.spreadsheets().values().get(
            spreadsheetId=gs_id,
            range=f"{sheet_name}!A:A"
        ).execute()
        total_rows = len(result.get("values", []))
        start_row = total_rows - len(rows)  # 0-indexed

        # 3) 시트 ID 가져오기
        sheet_meta = service.spreadsheets().get(spreadsheetId=gs_id).execute()
        sheet_id = 0
        for s in sheet_meta.get("sheets", []):
            if s["properties"]["title"] == sheet_name:
                sheet_id = s["properties"]["sheetId"]
                break

        # 4) 배경색 적용
        requests = []
        for i, row in enumerate(rows):
            status = row[11] if len(row) > 11 else ""
            if status == "성공":
                rgb = {"red": 0.851, "green": 0.918, "blue": 0.824}  # #d9ead2
            else:
                rgb = {"red": 0.957, "green": 0.800, "blue": 0.800}  # #f4cccc
            requests.append({
                "repeatCell": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": start_row + i,
                        "endRowIndex": start_row + i + 1,
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "backgroundColor": rgb
                        }
                    },
                    "fields": "userEnteredFormat.backgroundColor"
                }
            })

        if requests:
            service.spreadsheets().batchUpdate(
                spreadsheetId=gs_id,
                body={"requests": requests}
            ).execute()

        _log(f"구글시트 기록 완료: {len(rows)}행 → [{sheet_name}] (배경색 적용)")
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
# 원고 로더 (폴더 기반)
# ═══════════════════════════════════════════════

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}


def load_manuscripts(root_folder):
    """
    대폴더 경로를 받아 소폴더들을 스캔하여 원고 리스트 반환.
    소폴더 1개 = 키워드 1개 = 원고 1세트.

    반환: [
        {
            "folder": 소폴더 절대경로,
            "name": 소폴더명 (키워드),
            "title": "#제목" 파싱 결과,
            "body_parts": [str|{"type":"photo","files":[path,...]},...],
            "images": [이미지 절대경로 리스트 (파일명 오름차순)],
        }, ...
    ]
    리스트는 랜덤 셔플된 상태로 반환.
    """
    if not root_folder or not os.path.isdir(root_folder):
        return []

    manuscripts = []
    for entry in os.listdir(root_folder):
        sub = os.path.join(root_folder, entry)
        if not os.path.isdir(sub):
            continue

        # 재귀: 소폴더 안에 또 폴더가 있으면 그 안의 폴더들도 소폴더로 취급
        has_child_dirs = any(os.path.isdir(os.path.join(sub, c)) for c in os.listdir(sub))
        if has_child_dirs:
            # 이건 대폴더 역할 → 하위 소폴더들을 재귀 스캔
            manuscripts.extend(load_manuscripts(sub))
        else:
            ms = _parse_manuscript_folder(sub)
            if ms:
                manuscripts.append(ms)

    manuscripts.sort(key=lambda m: m["name"])
    return manuscripts


def _parse_manuscript_folder(folder_path):
    """소폴더 1개를 파싱하여 원고 dict 반환."""
    files = os.listdir(folder_path)

    # 이미지 수집 (파일명 오름차순)
    images = sorted(
        [os.path.join(folder_path, f) for f in files if os.path.splitext(f)[1].lower() in IMAGE_EXTS],
        key=lambda p: os.path.basename(p).lower()
    )

    # txt 파일 찾기 (첫 번째 txt)
    txt_files = [f for f in files if f.lower().endswith(".txt")]
    if not txt_files:
        return None

    txt_path = os.path.join(folder_path, txt_files[0])
    try:
        with open(txt_path, "r", encoding="utf-8") as f:
            raw = f.read()
    except:
        try:
            with open(txt_path, "r", encoding="cp949") as f:
                raw = f.read()
        except:
            return None

    title, body_parts, tags = _parse_txt(raw, images)

    return {
        "folder": folder_path,
        "name": os.path.basename(folder_path),
        "title": title,
        "body_parts": body_parts,
        "tags": tags,
        "images": images,
    }


def _parse_txt(raw_text, images):
    """
    txt 파일 파싱.
    #제목 → 제목
    #본문 → 본문 (내부에 #사진 태그 포함)

    body_parts: 텍스트와 이미지 삽입 지점을 구분한 리스트
      - str: 텍스트 블록
      - {"type": "photo", "files": [path, ...]}:
          files가 1개면 단일 이미지, 2개 이상이면 콜라주 대상

    반환: (title, body_parts)
    """
    title = ""
    body_raw = ""

    # #제목 / #본문 / #태그 분리
    lines = raw_text.replace("\r\n", "\n").split("\n")
    section = None
    title_lines = []
    body_lines = []
    tag_lines = []

    for line in lines:
        stripped = line.strip()
        if stripped == "#제목":
            section = "title"
            continue
        elif stripped == "#본문":
            section = "body"
            continue
        elif stripped == "#태그":
            section = "tag"
            continue
        # #댓글 등 다른 태그는 무시
        elif stripped.startswith("#") and stripped not in ("#사진", "사진 :", "사진:") and section != "body":
            section = "ignore"
            continue

        if section == "title":
            title_lines.append(line)
        elif section == "body":
            body_lines.append(line)
        elif section == "tag":
            if stripped:  # 빈 줄 무시
                tag_lines.append(stripped)

    title = "\n".join(title_lines).strip()
    body_raw = "\n".join(body_lines)

    # body에서 #사진 태그 처리
    # 연속 #사진은 콜라주로 묶어야 함
    body_parts = []
    img_idx = 0

    # 줄 단위로 처리하여 연속 #사진 감지
    buf_text = []
    buf_photos = []  # 연속 #사진에 매핑될 이미지 경로들

    for line in body_raw.split("\n"):
        if line.strip() in ("#사진", "사진 :", "사진:"):
            # 텍스트 버퍼가 있으면 먼저 flush
            if buf_text:
                body_parts.append("\n".join(buf_text))
                buf_text = []
            # 이미지 매핑
            if img_idx < len(images):
                buf_photos.append(images[img_idx])
                img_idx += 1
            else:
                buf_photos.append(None)  # 이미지 부족
        else:
            # #사진이 아닌 줄 → 연속 사진 버퍼 flush
            if buf_photos:
                valid = [p for p in buf_photos if p]
                if valid:
                    body_parts.append({"type": "photo", "files": valid})
                buf_photos = []
            buf_text.append(line)

    # 남은 버퍼 flush
    if buf_photos:
        valid = [p for p in buf_photos if p]
        if valid:
            body_parts.append({"type": "photo", "files": valid})
    if buf_text:
        text = "\n".join(buf_text).strip()
        if text:
            body_parts.append(text)

    return title, body_parts, tag_lines


def create_collage(image_paths, output_path=None):
    """
    이미지들을 횡방향(가로)으로 병합하여 콜라주 생성.
    높이는 가장 큰 이미지에 맞추고, 나머지는 비율 유지하며 리사이즈.

    Args:
        image_paths: 이미지 파일 경로 리스트
        output_path: 저장 경로 (None이면 임시파일)

    Returns:
        저장된 콜라주 이미지 경로
    """
    if not image_paths:
        return None
    if len(image_paths) == 1:
        return image_paths[0]  # 1장이면 그대로

    imgs = [PILImage.open(p) for p in image_paths]

    # 최대 높이에 맞춰 리사이즈
    max_h = max(img.height for img in imgs)
    resized = []
    for img in imgs:
        if img.height != max_h:
            ratio = max_h / img.height
            new_w = int(img.width * ratio)
            img = img.resize((new_w, max_h), PILImage.LANCZOS)
        resized.append(img)

    total_w = sum(img.width for img in resized)
    collage = PILImage.new("RGB", (total_w, max_h), (255, 255, 255))

    x = 0
    for img in resized:
        collage.paste(img, (x, 0))
        x += img.width

    if not output_path:
        import tempfile
        fd, output_path = tempfile.mkstemp(suffix=".jpg")
        os.close(fd)

    collage.save(output_path, "JPEG", quality=92)
    for img in imgs:
        img.close()
    for img in resized:
        try:
            img.close()
        except:
            pass

    return output_path


def randomize_image(image_path, output_path=None):
    """
    이미지 해시값/픽셀을 미세 변경하여 스팸 필터 회피.
    - 가로/세로 1~5px 랜덤 조정
    - JPEG 품질 랜덤 (88~95)
    - 1px 투명 노이즈 추가

    Args:
        image_path: 원본 이미지 경로
        output_path: 저장 경로 (None이면 임시파일)

    Returns:
        변경된 이미지 경로
    """
    import tempfile
    img = PILImage.open(image_path)

    # 가로/세로 1~5px 랜덤 조정
    dw = random.randint(-5, 5)
    dh = random.randint(-5, 5)
    new_w = max(10, img.width + dw)
    new_h = max(10, img.height + dh)
    img = img.resize((new_w, new_h), PILImage.LANCZOS)

    # RGB 변환 (RGBA/P 모드 대응)
    if img.mode != "RGB":
        img = img.convert("RGB")

    # 랜덤 픽셀 노이즈 (모서리 1px에 미세 변경)
    pixels = img.load()
    for _ in range(random.randint(1, 3)):
        rx = random.randint(0, new_w - 1)
        ry = random.randint(0, new_h - 1)
        r, g, b = pixels[rx, ry]
        pixels[rx, ry] = (
            max(0, min(255, r + random.randint(-2, 2))),
            max(0, min(255, g + random.randint(-2, 2))),
            max(0, min(255, b + random.randint(-2, 2))),
        )

    if not output_path:
        fd, output_path = tempfile.mkstemp(suffix=".jpg")
        os.close(fd)

    quality = random.randint(88, 95)
    img.save(output_path, "JPEG", quality=quality)
    img.close()
    return output_path


def prepare_images_for_upload(body_parts, delete_after=False, log_fn=None):
    """
    원고의 body_parts에서 이미지를 처리하여 업로드 준비.
    - 단일 사진: randomize_image → {"type": "photo", "path": ...}
    - 연속 사진(2장+): 개별 randomize_image → {"type": "slide", "paths": [...]}

    Args:
        body_parts: _parse_txt에서 반환된 body_parts
        delete_after: True면 처리 후 원본 삭제
        log_fn: 로그 콜백

    Returns:
        processed_parts:
            [str | {"type": "photo", "path": ...} | {"type": "slide", "paths": [...]}, ...]
    """
    _log = log_fn or (lambda msg: logger.info(msg))
    processed = []
    originals_to_delete = []

    for part in body_parts:
        if isinstance(part, str):
            processed.append(part)
        elif isinstance(part, dict) and part.get("type") == "photo":
            files = part.get("files", [])
            if not files:
                continue
            try:
                if len(files) == 1:
                    out = randomize_image(files[0])
                    processed.append({"type": "photo", "path": out})
                    _log(f"이미지 처리: 1장 → {os.path.basename(out)}")
                else:
                    paths = [randomize_image(f) for f in files]
                    processed.append({"type": "slide", "paths": paths})
                    _log(f"슬라이드 이미지 처리: {len(files)}장")
                originals_to_delete.extend(files)
            except Exception as e:
                _log(f"이미지 처리 실패: {str(e)[:60]}")

    if delete_after:
        for f in originals_to_delete:
            try:
                os.remove(f)
                _log(f"원본 삭제: {os.path.basename(f)}")
            except:
                pass

    return processed


def get_manuscript_display_list(root_folder):
    """대폴더 스캔 → 소폴더 리스트 (랜덤 순서). GUI 테이블용."""
    if not root_folder or not os.path.isdir(root_folder):
        return []

    result = []

    def _scan(folder):
        for entry in sorted(os.listdir(folder)):
            sub = os.path.join(folder, entry)
            if not os.path.isdir(sub):
                continue
            children = [c for c in os.listdir(sub) if os.path.isdir(os.path.join(sub, c))]
            if children:
                _scan(sub)  # 대폴더 → 재귀
            else:
                # 소폴더: 파일 카운트
                files = os.listdir(sub)
                txt_count = len([f for f in files if f.lower().endswith(".txt")])
                img_count = len([f for f in files if os.path.splitext(f)[1].lower() in IMAGE_EXTS])
                result.append({
                    "name": entry,
                    "path": sub,
                    "txt_count": txt_count,
                    "img_count": img_count,
                })

    _scan(root_folder)
    result.sort(key=lambda x: x["name"])
    return result


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
    filepath = os.path.join(_get_base_dir(), "changed_passwords.txt")
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


def create_driver(proxy_str=None, worker_id=0, chrome_version=None):
    import tempfile
    user_data = os.path.join(tempfile.gettempdir(), f"uc_worker_{worker_id}")

    # 생성 시도, 실패하면 정리 후 재시도
    for attempt in range(2):
        try:
            opts = uc.ChromeOptions()
            if proxy_str:
                opts.add_argument(f"--proxy-server={proxy_str}")
            opts.add_argument("--disable-backgrounding-occluded-windows")
            opts.add_argument("--disable-renderer-backgrounding")
            opts.add_argument("--disable-popup-blocking")
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
        if "비정상적인 활동" in page or "보호(잠금) 조치" in page or "보호하고 있습니다" in page or "idSafetyRelease" in url or "로그인 제한" in page or "로그인제한" in page:
            return {"ok": False, "msg": "보호조치 감지", "error": "needs_protection", "url": url, "page": page}

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
            if "보호조치 해제" in txt or "보호 조치 해제" in txt or "로그인 제한 해제" in txt:
                btn.click()
                time.sleep(3)
                dismiss_alert(driver)
                # 휴대전화 인증만 있는지 빠르게 판별 (implicitly_wait 짧게)
                driver.implicitly_wait(1)
                try:
                    has_birthday = bool(driver.find_elements(By.CSS_SELECTOR, "input#r_birthDate, input[value='birthDate']"))
                    has_phone = bool(driver.find_elements(By.CSS_SELECTOR, "input#r_phoneNo, input[value='phoneNo'], #ck_userMobile, label[id='ck_userMobile']"))
                    if has_phone and not has_birthday:
                        _log("보호조치 - 휴대전화 인증만 존재 (해제 불가)")
                        return {"ok": False, "msg": "보호조치 - 핸드폰 인증 (해제 불가)", "error": "blocked_phone"}
                    # 페이지 텍스트로도 판별
                    url2, page2 = get_page_safe(driver)
                    if ("본인 명의 휴대전화" in page2 or "userMobile" in page2) and not has_birthday:
                        _log("보호조치 - 휴대전화 인증만 존재 (해제 불가)")
                        return {"ok": False, "msg": "보호조치 - 핸드폰 인증 (해제 불가)", "error": "blocked_phone"}
                finally:
                    driver.implicitly_wait(5)
                # 생년월일 입력 시도
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
            captcha_passed = False
            for try_i in range(3):
                if _solve_text_captcha(driver, _log):
                    for btn in driver.find_elements(By.CSS_SELECTOR, "button, a, input[type='submit']"):
                        try:
                            if btn.text.strip() == "확인":
                                btn.click()
                                break
                        except:
                            continue
                    # 확인 후 3초 대기 → 에러 요소 확인
                    time.sleep(3)
                    err_el = driver.find_elements(By.CSS_SELECTOR, "div#e_autoValue")
                    if err_el and err_el[0].is_displayed() and ("잘못된" in err_el[0].text or "다시 입력" in err_el[0].text):
                        _log(f"자동입력 방지 문자 틀림 ({try_i+1}/3): {err_el[0].text.strip()[:40]}")
                        continue
                    captcha_passed = True
                    break
                else:
                    _log(f"캡차 인식 실패 ({try_i+1}/3)")

            if not captcha_passed:
                _log("캡차 3회 실패 — 보호조치 해제 실패")
                return {"ok": False, "msg": "보호조치 - 캡차 실패", "error": "captcha"}

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
        time.sleep(1.5)
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

        grade_info = {"my_grade": -1, "my_grade_text": "", "grades": {}, "grade_order": {}, "name_to_idx": {}, "level_to_idx": {}, "is_member": result.get("isCafeMember", False), "clubid": club_id}
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
            grade_info["name_to_idx"][name] = idx  # "독취주임" → 1
            grade_info["level_to_idx"][level] = idx  # 110 → 1
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
                        time.sleep(0.2)
                except:
                    continue
        for btn in driver.find_elements(By.CSS_SELECTOR, "button, a"):
            try:
                if btn.text.strip() == "닫기" and btn.is_displayed():
                    btn.click()
                    time.sleep(0.2)
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
        # 이미 해당 카페에 있으면 재접속 안 함
        cafe_id = cafe_url.rstrip("/").split("/")[-1]
        current = driver.current_url or ""
        if cafe_id not in current:
            _log(f"카페 접속: {cafe_url}")
            driver.get(cafe_url)
            time.sleep(1)
            dismiss_alert(driver)
            _close_cafe_popups(driver)
        else:
            _log(f"카페 이미 접속 중: {cafe_id}")

        url, page = get_page_safe(driver)

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
            time.sleep(1)
            _log(f"지정 게시판 이동: 메뉴ID={menu_id}")
            return {"ok": True, "msg": f"카페 접속 + 게시판 이동 (메뉴ID: {menu_id})", "menu_id": menu_id}

        # 메뉴 ID 없으면 자동 탐색은 나중에 구현
        return {"ok": True, "msg": "카페 접속 성공 (게시판 미지정)", "menu_id": ""}

    except Exception as e:
        return {"ok": False, "msg": f"카페 접속 에러: {str(e)[:60]}"}


# ═══════════════════════════════════════════════
# 게시글 목록 가져오기
# ═══════════════════════════════════════════════

def find_writable_board(driver, cafe_url, cafe_grades=None, log_fn=None):
    """카페에서 글쓰기 가능한 게시판 자동 탐색 (API). 메뉴ID 반환."""
    _log = log_fn or (lambda msg: logger.info(msg))
    try:
        # clubid — cafe_grades에서 가져오기
        clubid = ""
        if cafe_grades and cafe_url in cafe_grades:
            clubid = cafe_grades[cafe_url].get("clubid", "")

        if not clubid:
            _log("clubid 없음")
            return ""

        # 에디터 메뉴 API 호출 (writable 필드로 글쓰기 가능 여부 확인)
        import json, requests as req
        api_url = f"https://apis.naver.com/cafe-web/cafe-cafeinfo-api/v1.0/cafes/{clubid}/editor/menus"

        cookies = {c["name"]: c["value"] for c in driver.get_cookies()}
        headers = {
            "Referer": cafe_url,
            "Origin": "https://cafe.naver.com",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36",
            "x-cafe-product": "pc",
        }
        resp = req.get(api_url, cookies=cookies, headers=headers)
        _log(f"에디터 메뉴 API 상태: {resp.status_code}")

        if resp.status_code != 200:
            _log(f"에디터 메뉴 API 실패: {resp.status_code}")
            return ""

        data = resp.json()
        menus = data.get("result", [])

        # writable: true인 일반 게시판만 필터
        writable_boards = [m for m in menus if m.get("writable") and m.get("menuType") == "B"]
        _log(f"글쓰기 가능 게시판 {len(writable_boards)}개 / 전체 {len(menus)}개")

        if writable_boards:
            board = random.choice(writable_boards)
            _log(f"선택 게시판: {board['menuName']} (메뉴ID: {board['menuId']}, writeLevel: {board.get('writeLevel')})")
            return str(board["menuId"])

        _log("글쓰기 가능한 게시판 없음")
        return ""

    except Exception as e:
        _log(f"게시판 탐색 실패: {str(e)[:60]}")
        return ""


def get_article_list(driver, cafe_url, menu_id, page=1, club_id=None, log_fn=None):
    """게시판 게시글 목록 API로 가져오기."""
    _log = log_fn or (lambda msg: logger.info(msg))
    try:
        import json

        if not club_id:
            _log("❌ clubid 없음")
            return []

        api_url = f"https://apis.naver.com/cafe-web/cafe-boardlist-api/v1/cafes/{club_id}/menus/{menu_id}/articles?page={page}&pageSize=15&sortBy=TIME&viewType=L"
        _log(f"게시글 API 호출: clubid={club_id}, 메뉴ID={menu_id}, 페이지={page}")

        resp_text = driver.execute_script(
            "var x=new XMLHttpRequest();x.open('GET',arguments[0],false);x.withCredentials=true;x.send();return x.responseText;",
            api_url
        )
        data = json.loads(resp_text)
        article_list = data.get("result", {}).get("articleList", [])

        if not article_list:
            _log(f"페이지 {page}: 게시글 없음")
            return []

        articles = []
        for item_wrap in article_list:
            item = item_wrap.get("item", {})
            writer = item.get("writerInfo", {})
            articles.append({
                "article_id": str(item.get("articleId", "")),
                "title": item.get("subject", ""),
                "author_grade": writer.get("memberLevelName", ""),
                "author_grade_level": writer.get("memberLevel", -1),
                "author_nick": writer.get("nickName", "") or writer.get("nickname", ""),
                "secede_member": writer.get("secedeMember", False),
                "cafe_id": str(item.get("cafeId", "")),
            })

        _log(f"게시글 {len(articles)}개 수집 완료 (페이지 {page})")
        return articles

    except Exception as e:
        _log(f"게시글 목록 실패: {str(e)[:60]}")
        return []


# ═══════════════════════════════════════════════
# 답글 작성 (게시글 하단 "답글" 버튼 → 새 게시글 에디터)
# ═══════════════════════════════════════════════

def write_reply(driver, cafe_url, article_id, title, processed_parts, options=None, tags=None, log_fn=None):
    """
    게시글의 '답글' 버튼을 클릭하여 답글 게시글 작성.
    답글 = 해당 글에 대한 새 게시글 (댓글 아님).

    Args:
        driver: 로그인된 드라이버
        cafe_url: 카페 URL
        article_id: 원본 게시글 ID
        title: 답글 제목
        processed_parts: prepare_images_for_upload 결과 또는 텍스트
        options: {"allow_comment": bool, "allow_search": bool, "public": bool}
        log_fn: 로그 콜백

    Returns:
        {"ok": bool, "url": str}
    """
    _log = log_fn or (lambda msg: logger.info(msg))
    options = options or {}
    tags = tags or []

    try:
        # 게시글 접속
        article_url = f"{cafe_url}?iframe_url=/ArticleRead.nhn%3Farticleid%3D{article_id}"
        _log(f"게시글 접속: article_id={article_id}")
        driver.get(article_url)
        time.sleep(1.5)

        # iframe 전환
        try:
            iframe = driver.find_element(By.CSS_SELECTOR, "iframe#cafe_main")
            driver.switch_to.frame(iframe)
            _log("iframe 전환 완료")
            time.sleep(0.5)
        except:
            _log("iframe 없음 — 메인 프레임에서 진행")

        # "답글" 버튼 찾기 & 클릭
        _log("답글 버튼 탐색 중...")
        reply_btn = None
        # 방법1: 텍스트가 "답글"인 버튼/링크
        for el in driver.find_elements(By.CSS_SELECTOR, "a, button"):
            try:
                txt = el.text.strip()
                if txt == "답글" and el.is_displayed():
                    reply_btn = el
                    break
            except:
                continue
        # 방법2: class에 reply 포함
        if not reply_btn:
            candidates = driver.find_elements(By.CSS_SELECTOR, "a[class*='reply'], a[class*='Reply'], button[class*='reply']")
            for c in candidates:
                try:
                    if c.is_displayed():
                        reply_btn = c
                        break
                except:
                    continue

        if not reply_btn:
            _log("❌ 답글 버튼 못 찾음 — 이 글은 답글 불가")
            driver.switch_to.default_content()
            return {"ok": False, "url": ""}

        # 답글 버튼의 href에서 에디터 URL 추출 또는 직접 클릭
        reply_href = reply_btn.get_attribute("href") or ""
        _log(f"답글 버튼 발견 — 클릭")
        reply_btn.click()
        time.sleep(1.5)
        driver.switch_to.default_content()

        # 에디터 페이지로 전환됨 (새 탭이 열릴 수도 있음)
        # 탭이 여러 개면 마지막 탭으로 전환
        if len(driver.window_handles) > 1:
            driver.switch_to.window(driver.window_handles[-1])
            _log("새 탭으로 전환")
            time.sleep(1)

        # 에디터 로드 대기
        # 활동정지 alert 체크
        try:
            from selenium.webdriver.common.alert import Alert as _Alert
            alert = _Alert(driver)
            alert_text = alert.text
            if "활동정지" in alert_text or "활동 정지" in alert_text:
                alert.accept()
                _log(f"❌ 활동정지 상태: {alert_text[:50]}")
                if len(driver.window_handles) > 1:
                    driver.close()
                    driver.switch_to.window(driver.window_handles[0])
                return {"ok": False, "url": "", "error": "suspended"}
            alert.accept()
        except:
            pass  # alert 없으면 정상

        current_url = driver.current_url
        _log(f"에디터 페이지: {current_url[:60]}")

        # 제목 입력
        _log("제목 입력 영역 탐색...")
        title_input = driver.find_elements(By.CSS_SELECTOR, "textarea.textarea_input, input.se-title-input, textarea[placeholder*='제목']")
        if not title_input:
            title_input = driver.find_elements(By.CSS_SELECTOR, "[class*='title'] textarea, [class*='title'] input")
        if title_input:
            title_input[0].click()
            time.sleep(0.1)
            with _clipboard_lock:
                pyperclip.copy(title)
                title_input[0].send_keys(Keys.CONTROL, "a")
                title_input[0].send_keys(Keys.CONTROL, "v")
            time.sleep(0.1)
            _log(f"제목 입력 완료: {title[:30]}")
        else:
            _log("⚠ 제목 입력 영역 못 찾음 — 기본 제목 사용")

        # 본문 영역 클릭
        body_area = driver.find_elements(By.CSS_SELECTOR, ".se-component-content .se-text-paragraph, div.se-content, div[contenteditable='true']")
        if not body_area:
            body_area = driver.find_elements(By.CSS_SELECTOR, "[class*='editor'] [contenteditable], .article_editor")
        if body_area:
            body_area[0].click()
            time.sleep(0.2)
            _log("본문 영역 활성화")

        # 본문 파트 입력
        text_count = 0
        img_count = 0
        parts = processed_parts if isinstance(processed_parts, list) else []

        # 문자열이 넘어온 경우 (하위 호환)
        if isinstance(processed_parts, str):
            parts = [processed_parts]

        for part in parts:
            if isinstance(part, str):
                if not part.strip():
                    continue
                body_el = driver.switch_to.active_element
                with _clipboard_lock:
                    pyperclip.copy(part)
                    body_el.send_keys(Keys.CONTROL, "v")
                time.sleep(0.1)
                body_el.send_keys(Keys.ENTER)
                time.sleep(0.1)
                text_count += 1
            elif isinstance(part, dict) and part.get("type") == "photo":
                img_path = part.get("path", "")
                if not img_path or not os.path.isfile(img_path):
                    continue
                photo_btn = driver.find_elements(By.CSS_SELECTOR, "button[data-name='image'], button[data-log='dot.img']")
                if photo_btn:
                    photo_btn[0].click()
                    time.sleep(0.5)
                file_input = driver.find_elements(By.CSS_SELECTOR, "input#hidden-file, input[type='file'][accept*='.jpg']")
                if file_input:
                    file_input[0].send_keys(os.path.abspath(img_path))
                    time.sleep(1)
                    img_count += 1
                    _log(f"이미지 업로드 {img_count}: {os.path.basename(img_path)}")
                else:
                    _log("❌ 이미지 업로드 input 못 찾음")
            elif isinstance(part, dict) and part.get("type") == "slide":
                paths = [p for p in part.get("paths", []) if p and os.path.isfile(p)]
                if not paths:
                    continue
                photo_btn = driver.find_elements(By.CSS_SELECTOR, "button[data-name='image'], button[data-log='dot.img']")
                if photo_btn:
                    photo_btn[0].click()
                    time.sleep(0.5)
                file_input = driver.find_elements(By.CSS_SELECTOR, "input#hidden-file, input[type='file'][accept*='.jpg']")
                if file_input:
                    file_input[0].send_keys("\n".join(os.path.abspath(p) for p in paths))
                    time.sleep(1.5)
                    # 슬라이드 버튼 클릭
                    slide_btn = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, "#image-type-collage"))
                    )
                    slide_btn.click()
                    time.sleep(1)
                    img_count += len(paths)
                    _log(f"슬라이드 업로드 {len(paths)}장")
                else:
                    _log("❌ 이미지 업로드 input 못 찾음")

        _log(f"본문 입력 완료: 텍스트 {text_count}개, 이미지 {img_count}개")

        # 태그 입력
        _input_tags(driver, tags, _log)

        # 옵션 설정
        _set_post_options(driver, options, _log)

        # 등록 버튼 클릭
        time.sleep(0.5)
        register_btn = driver.find_elements(By.CSS_SELECTOR, "a.BaseButton--skinGreen .BaseButton__txt, a.BaseButton--skinGreen")
        clicked = False
        for btn in register_btn:
            try:
                if "등록" in btn.text.strip():
                    _log(f"등록 버튼 클릭: [{btn.text.strip()}]")
                    btn.click()
                    time.sleep(2)
                    clicked = True
                    break
            except:
                continue

        if not clicked:
            _log("❌ 등록 버튼 못 찾음")
            if len(driver.window_handles) > 1:
                driver.close()
                driver.switch_to.window(driver.window_handles[0])
            return {"ok": False, "url": ""}

        dismiss_alert(driver)
        post_url = driver.current_url
        _log(f"답글 게시글 등록 완료 — URL: {post_url[:60]}")

        # 에디터 탭 닫고 원래 탭으로
        if len(driver.window_handles) > 1:
            driver.close()
            driver.switch_to.window(driver.window_handles[0])

        return {"ok": True, "url": post_url}

    except Exception as e:
        _log(f"❌ 답글 작성 예외: {str(e)[:60]}")
        try:
            if len(driver.window_handles) > 1:
                driver.close()
                driver.switch_to.window(driver.window_handles[0])
            else:
                driver.switch_to.default_content()
        except:
            pass
        return {"ok": False, "url": ""}


# ═══════════════════════════════════════════════
# 글쓰기 (새 게시글 작성)
# ═══════════════════════════════════════════════

def write_post(driver, cafe_url, menu_id, title, processed_parts, options=None, tags=None, log_fn=None):
    """
    카페에 새 게시글 작성 (에디터).

    Args:
        driver: 로그인된 드라이버
        cafe_url: 카페 URL
        menu_id: 게시판 메뉴 ID
        title: 글 제목
        processed_parts: prepare_images_for_upload 결과
            [str | {"type": "photo", "path": 이미지경로}, ...]
        options: {"allow_comment": bool, "allow_search": bool, "public": bool}
        log_fn: 로그 콜백

    Returns:
        {"ok": bool, "url": str, "msg": str}
    """
    _log = log_fn or (lambda msg: logger.info(msg))
    options = options or {}
    tags = tags or []

    try:
        # 에디터 페이지 접속
        cafe_id = cafe_url.rstrip("/").split("/")[-1]
        editor_url = f"https://cafe.naver.com/ca-fe/cafes/{cafe_id}/menus/{menu_id}/articles/write"
        _log(f"에디터 접속: {editor_url}")
        driver.get(editor_url)
        time.sleep(1.5)
        dismiss_alert(driver)

        # 제목 입력
        _log("제목 입력 영역 탐색...")
        title_input = driver.find_elements(By.CSS_SELECTOR, "textarea.textarea_input, input.se-title-input, textarea[placeholder*='제목']")
        if not title_input:
            title_input = driver.find_elements(By.CSS_SELECTOR, "[class*='title'] textarea, [class*='title'] input")
        if title_input:
            title_input[0].click()
            time.sleep(0.1)
            with _clipboard_lock:
                pyperclip.copy(title)
                title_input[0].send_keys(Keys.CONTROL, "a")
                title_input[0].send_keys(Keys.CONTROL, "v")
            time.sleep(0.1)
            _log(f"제목 입력 완료: {title[:30]}")
        else:
            _log("❌ 제목 입력 영역 못 찾음")
            return {"ok": False, "url": "", "msg": "제목 입력 실패"}

        # 본문 영역 클릭
        _log("본문 영역 탐색...")
        body_area = driver.find_elements(By.CSS_SELECTOR, ".se-component-content .se-text-paragraph, div.se-content, div[contenteditable='true']")
        if not body_area:
            body_area = driver.find_elements(By.CSS_SELECTOR, "[class*='editor'] [contenteditable], .article_editor")
        if body_area:
            body_area[0].click()
            time.sleep(0.2)
            _log("본문 영역 활성화")
        else:
            _log("⚠ 본문 영역 못 찾음 — 계속 진행")

        # 본문 파트 순서대로 입력
        text_count = 0
        img_count = 0
        for part_idx, part in enumerate(processed_parts):
            if isinstance(part, str):
                if not part.strip():
                    continue
                body_el = driver.switch_to.active_element
                with _clipboard_lock:
                    pyperclip.copy(part)
                    body_el.send_keys(Keys.CONTROL, "v")
                time.sleep(0.1)
                body_el.send_keys(Keys.ENTER)
                time.sleep(0.1)
                text_count += 1
                _log(f"본문 텍스트 {text_count} 입력 ({len(part)}자)")
            elif isinstance(part, dict) and part.get("type") == "photo":
                img_path = part.get("path", "")
                if not img_path or not os.path.isfile(img_path):
                    _log(f"⚠ 이미지 파일 없음: {img_path}")
                    continue
                photo_btn = driver.find_elements(By.CSS_SELECTOR, "button[data-name='image'], button[data-log='dot.img']")
                if photo_btn:
                    photo_btn[0].click()
                    time.sleep(0.5)
                file_input = driver.find_elements(By.CSS_SELECTOR, "input#hidden-file, input[type='file'][accept*='.jpg']")
                if file_input:
                    file_input[0].send_keys(os.path.abspath(img_path))
                    time.sleep(1)
                    img_count += 1
                    _log(f"이미지 업로드 {img_count}: {os.path.basename(img_path)}")
                else:
                    _log("❌ 이미지 업로드 input 못 찾음")
            elif isinstance(part, dict) and part.get("type") == "slide":
                paths = [p for p in part.get("paths", []) if p and os.path.isfile(p)]
                if not paths:
                    continue
                photo_btn = driver.find_elements(By.CSS_SELECTOR, "button[data-name='image'], button[data-log='dot.img']")
                if photo_btn:
                    photo_btn[0].click()
                    time.sleep(0.5)
                file_input = driver.find_elements(By.CSS_SELECTOR, "input#hidden-file, input[type='file'][accept*='.jpg']")
                if file_input:
                    file_input[0].send_keys("\n".join(os.path.abspath(p) for p in paths))
                    time.sleep(1.5)
                    slide_btn = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, "#image-type-collage"))
                    )
                    slide_btn.click()
                    time.sleep(1)
                    img_count += len(paths)
                    _log(f"슬라이드 업로드 {len(paths)}장")
                else:
                    _log("❌ 이미지 업로드 input 못 찾음")

        _log(f"본문 입력 완료: 텍스트 {text_count}개, 이미지 {img_count}개")

        # 태그 입력
        _input_tags(driver, tags, _log)

        # 옵션 설정 (댓글허용, 검색허용, 전체공개)
        _log(f"옵션 설정: 댓글={options.get('allow_comment', True)}, 검색={options.get('allow_search', True)}, 공개={options.get('public', True)}")
        _set_post_options(driver, options, _log)

        # 등록 버튼
        _log("등록 버튼 탐색...")
        time.sleep(0.5)
        submit_btns = driver.find_elements(By.CSS_SELECTOR, "button.btn_submit, button[class*='register'], a.btn_register, button.BaseButton")
        clicked = False
        for btn in submit_btns:
            try:
                txt = btn.text.strip()
                if "등록" in txt or "작성" in txt:
                    _log(f"등록 버튼 클릭: [{txt}]")
                    btn.click()
                    time.sleep(1.5)
                    clicked = True
                    break
            except:
                continue

        if not clicked:
            _log("❌ 등록 버튼 못 찾음")
            return {"ok": False, "url": "", "msg": "등록 버튼 없음"}

        dismiss_alert(driver)
        post_url = driver.current_url
        _log(f"글쓰기 등록 완료 — URL: {post_url[:60]}")
        return {"ok": True, "url": post_url, "msg": "글쓰기 성공"}

    except Exception as e:
        _log(f"❌ 글쓰기 예외: {str(e)[:60]}")
        return {"ok": False, "url": "", "msg": str(e)[:60]}


def _input_tags(driver, tags, _log):
    """에디터에서 태그 입력. input.tag_input에 하나씩 입력 + Enter."""
    if not tags:
        return
    try:
        tag_input = driver.find_elements(By.CSS_SELECTOR, "input.tag_input")
        if not tag_input:
            _log("⚠ 태그 입력 영역 못 찾음")
            return
        for i, tag in enumerate(tags[:10]):  # 최대 10개
            tag_input[0].click()
            time.sleep(0.1)
            tag_input[0].clear()
            tag_input[0].send_keys(tag)
            time.sleep(0.1)
            tag_input[0].send_keys(Keys.ENTER)
            time.sleep(0.1)
        _log(f"태그 {min(len(tags), 10)}개 입력 완료")
    except Exception as e:
        _log(f"태그 입력 실패: {str(e)[:40]}")


def _set_post_options(driver, options, _log):
    """
    글쓰기 에디터에서 옵션 설정.
    1. button.btn_open_set 클릭 (공개설정 열기)
    2. 전체공개 / 멤버공개 라디오 선택
    3. 멤버공개일 때 검색허용 체크박스
    4. 댓글허용 체크박스
    """
    want_public = options.get("public", True)
    want_search = options.get("allow_search", True)
    want_comment = options.get("allow_comment", True)

    try:
        # 1. 공개설정 버튼 클릭
        open_btn = driver.find_elements(By.CSS_SELECTOR, "button.btn_open_set")
        if open_btn:
            open_btn[0].click()
            time.sleep(0.3)
            _log("공개설정 패널 열기")

        # 2. 전체공개 / 멤버공개 라디오
        if want_public:
            radio = driver.find_elements(By.CSS_SELECTOR, "input#all[name='public']")
            if radio and not radio[0].is_selected():
                driver.find_element(By.CSS_SELECTOR, "label[for='all']").click()
                time.sleep(0.2)
            _log("전체공개 선택")
        else:
            radio = driver.find_elements(By.CSS_SELECTOR, "input#member[name='public']")
            if radio and not radio[0].is_selected():
                driver.find_element(By.CSS_SELECTOR, "label[for='member']").click()
                time.sleep(0.2)
            _log("멤버공개 선택")

            # 3. 검색허용 체크박스 (멤버공개일 때만)
            search_cb = driver.find_elements(By.CSS_SELECTOR, "input#permit")
            if search_cb:
                is_checked = search_cb[0].is_selected()
                if want_search and not is_checked:
                    driver.find_element(By.CSS_SELECTOR, "label[for='permit']").click()
                    time.sleep(0.2)
                    _log("검색허용 체크")
                elif not want_search and is_checked:
                    driver.find_element(By.CSS_SELECTOR, "label[for='permit']").click()
                    time.sleep(0.2)
                    _log("검색허용 해제")

        # 4. 댓글허용 체크박스
        comment_cb = driver.find_elements(By.CSS_SELECTOR, "input#coment")
        if comment_cb:
            is_checked = comment_cb[0].is_selected()
            if want_comment and not is_checked:
                driver.find_element(By.CSS_SELECTOR, "label[for='coment']").click()
                time.sleep(0.2)
                _log("댓글허용 체크")
            elif not want_comment and is_checked:
                driver.find_element(By.CSS_SELECTOR, "label[for='coment']").click()
                time.sleep(0.2)
                _log("댓글허용 해제")

    except Exception as e:
        _log(f"옵션 설정 실패: {str(e)[:40]}")


# ═══════════════════════════════════════════════
# 카페 작업 실행 (OFF 모드: 지정 게시판 답글)
# ═══════════════════════════════════════════════

def _flatten_body(body_parts):
    """body_parts를 텍스트로 평탄화 (이미지 부분은 [사진] 표시)."""
    result = []
    for part in body_parts:
        if isinstance(part, str):
            result.append(part)
        elif isinstance(part, dict) and part.get("type") == "photo":
            result.append("[사진]")
    return "\n".join(result)


def do_cafe_work(driver, account, cafe_grades, settings, log_fn=None):
    """
    카페 작업 실행.
    - 메뉴ID 비어있으면 → 자동가입 트리거 + 글쓰기 가능 게시판 탐색
    - 작성 모드: "글쓰기" / "답글" / "글쓰기 + 답글"
    - 원고 랜덤 추출, 이미지 픽셀 랜덤 변경, 콜라주 처리
    - 결과: 작성된 답글/글 1개당 1행 반환 (결과시트용)

    Returns:
        {
            "ok": bool,
            "msg": str,
            "written": int,
            "result_rows": [  # 작성된 글 1개당 1행
                {"id": str, "pw": str, "name": str, "birth": str, "gender": str,
                 "url": str, "deleted": False},
                ...
            ]
        }
    """
    _log = log_fn or (lambda msg: logger.info(msg))
    cafe_url = account.get("cafe_url", "")
    menu_id = account.get("menu_id", "")
    post_count = account.get("post_count", 1)
    write_mode = settings.get("write_mode", "답글")
    delete_images = settings.get("delete_images", False)
    post_options = settings.get("post_options", {})

    # ── 카페 미가입 시 자동가입 (워커 스레드에서 이미 판별 후 호출됨) ──
    # visit_cafe는 워커 스레드에서 이미 호출했으므로 여기서는 스킵

    # ── 메뉴ID 없으면 글쓰기 가능 게시판 자동 탐색 ──
    if not menu_id:
        _log("메뉴ID 없음 - 글쓰기 가능 게시판 자동 탐색")
        menu_id = find_writable_board(driver, cafe_url, cafe_grades, _log)
        if not menu_id:
            _log("글쓰기 가능한 게시판 못 찾음")
            return {"ok": False, "msg": "글쓰기 가능 게시판 없음", "written": 0, "result_rows": []}

    _log(f"[설정] 모드={write_mode} / 게시판={menu_id} / 목표={post_count}개 / 이미지삭제={delete_images}")

    written = 0
    result_rows = []
    manuscripts = settings.get("ms_assignments", {}).get(account.get("id", ""), settings.get("manuscripts", []))
    contents = settings.get("contents", [])
    if not manuscripts and not contents:
        _log("원고 없음")
        return {"ok": False, "msg": "원고 없음", "written": 0, "result_rows": []}

    page_lo = settings.get("page_lo", 1)
    page_hi = settings.get("page_hi", 10)
    delay_lo = settings.get("delay_lo", 3)
    delay_hi = settings.get("delay_hi", 8)
    grade_filter = settings.get("grade_filter", list(range(6)))
    _log(f"[설정] 페이지={page_lo}~{page_hi} / 딜레이={delay_lo}~{delay_hi}초")

    # 카페 등급 정보
    grade_info = cafe_grades.get(cafe_url, {})

    # 결과 행 기본 정보
    row_base = {
        "id": account.get("id", ""),
        "pw": account.get("pw", ""),
        "name": account.get("name", ""),
        "birth": account.get("birth", ""),
        "gender": account.get("gender", ""),
    }

    # ── 글쓰기 모드 ──
    if write_mode in ("글쓰기", "글쓰기 + 답글"):
        _log(f"[글쓰기 모드] 목표: {post_count}개 / 게시판: {menu_id}")
        for i in range(post_count):
            if written >= post_count:
                _log(f"목표 달성 ({written}/{post_count}) — 글쓰기 종료")
                break

            ms = manuscripts[written] if written < len(manuscripts) else None
            if not ms:
                _log("배정된 원고 소진 — 글쓰기 중단")
                break

            _log(f"글쓰기 {i+1}/{post_count}: 원고=[{ms['name']}] 제목=[{ms.get('title', '')[:30]}]")
            _log(f"이미지 처리 시작 (파트 {len(ms.get('body_parts', []))}개)")
            processed = prepare_images_for_upload(ms.get("body_parts", []), delete_after=delete_images, log_fn=_log)
            _log(f"이미지 처리 완료 → 에디터 작성 시작")
            result = write_post(driver, cafe_url, menu_id, ms.get("title", ""), processed, post_options, ms.get("tags", []), _log)

            if result.get("ok"):
                written += 1
                result_rows.append({**row_base, "cafe_url": cafe_url, "menu_id": menu_id, "url": result["url"], "deleted": "미확인", "manuscript": ms['name'], "status": "성공", "error": ""})
                _log(f"✅ 글쓰기 {written}/{post_count} 완료 — URL: {result['url'][:60]}")
                _cleanup_temp_images(processed)
                delay = random.randint(delay_lo, delay_hi)
                _log(f"딜레이 {delay}초 대기...")
                time.sleep(delay)
            else:
                _cleanup_temp_images(processed)
                _log(f"❌ 글쓰기 실패: {result.get('msg', '')}")
                result_rows.append({**row_base, "cafe_url": cafe_url, "menu_id": menu_id, "url": "", "deleted": "", "manuscript": ms['name'], "status": "실패", "error": result.get('msg', '')})

        if write_mode == "글쓰기":
            _log(f"=== 카페 작업 완료: {written}/{post_count}개 작성 ===")
            return {"ok": written > 0, "msg": f"{written}/{post_count}개 작성", "written": written, "result_rows": result_rows}

    # ── 답글 모드 ──
    if write_mode in ("답글", "글쓰기 + 답글"):
        reply_target = post_count - written if write_mode == "글쓰기 + 답글" else post_count
        reply_written = 0
        _log(f"[답글 모드] 목표: {reply_target}개 / 페이지 범위: {page_lo}~{page_hi}")

        for page in range(page_lo, page_hi + 1):
            if reply_written >= reply_target:
                _log(f"목표 달성 ({reply_written}/{reply_target}) — 페이지 순회 종료")
                break

            _log(f"페이지 {page}/{page_hi} 게시글 수집 중...")
            articles = get_article_list(driver, cafe_url, menu_id, page, club_id=grade_info.get("clubid", ""), log_fn=_log)

            if not articles:
                _log(f"페이지 {page}: 게시글 없음 — 다음 페이지 없으므로 종료")
                break

            filtered_count = 0
            for article in articles:
                if reply_written >= reply_target:
                    break

                # 등급 필터
                # API에서 secedeMember=True면 탈퇴회원 → idx=-1
                # 아니면 level_to_idx로 memberLevel → idx 변환
                is_secede = article.get("secede_member", False)
                if is_secede:
                    author_idx = -1
                else:
                    member_level = article.get("author_grade_level", -1)
                    level_to_idx = grade_info.get("level_to_idx", {})
                    author_idx = level_to_idx.get(member_level, -1)

                if grade_filter and author_idx not in grade_filter:
                    filtered_count += 1
                    continue

                # 원고 순차 배정
                if manuscripts and reply_written < len(manuscripts):
                    ms = manuscripts[reply_written]
                    _log(f"원고 배정: [{ms['name']}] ({reply_written+1}/{len(manuscripts)})")
                    processed = prepare_images_for_upload(ms.get("body_parts", []), delete_after=delete_images, log_fn=_log)
                    reply_title = ms.get("title", "")
                    reply_tags = ms.get("tags", [])
                elif manuscripts:
                    _log("배정된 원고 소진 — 답글 중단")
                    break
                else:
                    reply_title = ""
                    reply_tags = []
                    processed = [contents[reply_written % len(contents)] if contents else ""]

                _log(f"답글 작성 시도: [{article['title'][:30]}] article_id={article['article_id']} 등급={article.get('author_grade', '') or '탈퇴회원'} 닉={article.get('author_nick', '')}")
                result = write_reply(driver, cafe_url, article["article_id"], reply_title, processed, post_options, reply_tags, _log)

                if result.get("ok"):
                    reply_written += 1
                    written += 1
                    ms_name = ms['name'] if manuscripts else ""
                    result_rows.append({**row_base, "cafe_url": cafe_url, "menu_id": menu_id, "url": result["url"], "deleted": "미확인", "manuscript": ms_name, "status": "성공", "error": ""})
                    _log(f"✅ 답글 {reply_written}/{reply_target} 완료 — URL: {result['url'][:60]}")

                    _cleanup_temp_images(processed)

                    delay = random.randint(delay_lo, delay_hi)
                    _log(f"딜레이 {delay}초 대기...")
                    time.sleep(delay)
                else:
                    _log(f"❌ 답글 작성 실패: article_id={article['article_id']}")
                    _cleanup_temp_images(processed)
                    ms_name = ms['name'] if manuscripts else ""
                    result_rows.append({**row_base, "cafe_url": cafe_url, "menu_id": menu_id, "url": "", "deleted": "", "manuscript": ms_name, "status": "실패", "error": result.get('error', '') or "작성실패"})
                    # 활동정지면 즉시 종료
                    if result.get("error") == "suspended":
                        _log("활동정지 감지 — 카페 작업 중단")
                        return {"ok": False, "msg": "활동정지", "written": written, "result_rows": result_rows, "error": "suspended"}

            if filtered_count > 0:
                _log(f"페이지 {page}: 등급 필터로 {filtered_count}개 스킵")

    _log(f"=== 카페 작업 완료: {written}/{post_count}개 작성 ===")
    return {"ok": written > 0, "msg": f"{written}/{post_count}개 작성", "written": written, "result_rows": result_rows}


def _cleanup_temp_images(processed_parts):
    """prepare_images_for_upload에서 생성된 임시 이미지 삭제."""
    import tempfile
    tmp_dir = tempfile.gettempdir()
    for part in processed_parts:
        if isinstance(part, dict) and part.get("type") == "photo":
            p = part.get("path", "")
            if p and tmp_dir in p:
                try:
                    os.remove(p)
                except:
                    pass


def check_post_deleted(driver, url, log_fn=None):
    """URL 접속 후 삭제 여부 판단. 반환: '정상' 또는 '삭제됨'."""
    _log = log_fn or (lambda msg: logger.info(msg))
    try:
        driver.get(url)
        time.sleep(2)
        try:
            alert = driver.switch_to.alert
            alert_text = alert.text
            alert.accept()
            if "삭제" in alert_text or "존재하지 않는" in alert_text:
                return "삭제됨"
        except:
            pass
        return "정상"
    except Exception as e:
        _log(f"삭제 체크 실패 ({url[:40]}): {str(e)[:40]}")
        return "확인실패"


def update_gsheet_deleted(url_status_map, sheet_name="결과값", log_fn=None):
    """
    결과값 시트에서 URL(H열)을 찾아 삭제유무(I열)를 업데이트.
    url_status_map: {url: "정상"|"삭제됨"|"확인실패", ...}
    """
    _log = log_fn or (lambda msg: logger.info(msg))
    if not url_status_map:
        return
    cfg = load_config()
    gs_id = cfg.get("google_sheets", "sheet_id", fallback="")
    if not gs_id:
        return
    try:
        service = _get_sheets_service_write()
        if not service:
            return
        # H열(URL) 전체 읽기
        result = service.spreadsheets().values().get(
            spreadsheetId=gs_id,
            range=f"{sheet_name}!H:H"
        ).execute()
        h_values = result.get("values", [])

        # URL 매칭 → I열 업데이트 배치
        updates = []
        for row_idx, row in enumerate(h_values):
            if not row:
                continue
            cell_url = row[0].strip()
            if cell_url in url_status_map:
                updates.append({
                    "range": f"{sheet_name}!I{row_idx + 1}",
                    "values": [[url_status_map[cell_url]]]
                })

        if updates:
            service.spreadsheets().values().batchUpdate(
                spreadsheetId=gs_id,
                body={"valueInputOption": "USER_ENTERED", "data": updates}
            ).execute()
            _log(f"삭제유무 업데이트 완료: {len(updates)}건")
    except Exception as e:
        _log(f"삭제유무 업데이트 실패: {str(e)[:60]}")