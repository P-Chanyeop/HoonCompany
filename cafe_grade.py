"""
cafe_grade.py — 네이버 카페별 등급 파악 모듈
SOFTCAT | SC-2026-0410-CG

사용법:
    import func
    from cafe_grade import check_cafe_grade, batch_check_grades

    driver = func.create_driver(proxy, worker_id)
    func.naver_login(driver, account, log_fn=print)

    # 단일 카페 등급 조회 + 구글시트 기록
    result = check_cafe_grade(driver, "https://cafe.naver.com/dokchi", log_fn=print)

    # 다수 카페 일괄 조회 + 구글시트 기록
    results = batch_check_grades(driver, ["https://cafe.naver.com/dokchi", ...], log_fn=print)

의존성:
    - func.py (get_cafe_grades, append_to_gsheet)
"""

import logging
from datetime import datetime

import func

logger = logging.getLogger(__name__)


def check_cafe_grade(driver, cafe_url, log_fn=None, save_to_sheet=True):
    """
    카페 등급 체계를 조회하고 구글시트에 기록한다.

    Args:
        driver: 로그인된 셀레니움 드라이버
        cafe_url: 카페 URL
        log_fn: 로그 콜백
        save_to_sheet: 구글시트 기록 여부 (기본 True)

    Returns:
        dict: {
            "ok": bool,
            "cafe_url": str,
            "is_member": bool,
            "my_grade": str,
            "grades": [{"level": int, "name": str, "condition": str}, ...],
            "msg": str
        }
    """
    _log = log_fn or (lambda msg: logger.info(msg))

    grade_info = func.get_cafe_grades(driver, cafe_url, _log)

    if not grade_info.get("grades"):
        return {"ok": False, "cafe_url": cafe_url, "is_member": False, "my_grade": "", "grades": [], "msg": "등급 조회 실패"}

    # grade_order를 리스트로 정리
    grades = []
    for idx in sorted(grade_info.get("grade_order", {}).keys()):
        g = grade_info["grade_order"][idx]
        grades.append({"level": g["level"], "name": g["name"], "condition": g["cond"]})

    result = {
        "ok": True,
        "cafe_url": cafe_url,
        "is_member": grade_info.get("is_member", False),
        "my_grade": grade_info.get("my_grade_text", ""),
        "grades": grades,
        "msg": f"등급 {len(grades)}개 조회 완료"
    }

    if save_to_sheet:
        _save_grades_to_gsheet(cafe_url, grades, grade_info, _log)

    return result


def batch_check_grades(driver, cafe_urls, log_fn=None, save_to_sheet=True):
    """
    다수 카페의 등급 체계를 일괄 조회하고 구글시트에 기록한다.

    Args:
        driver: 로그인된 셀레니움 드라이버
        cafe_urls: [str, ...] 카페 URL 목록
        log_fn: 로그 콜백
        save_to_sheet: 구글시트 기록 여부

    Returns:
        list[dict]: 각 카페별 check_cafe_grade 결과
    """
    _log = log_fn or (lambda msg: logger.info(msg))
    results = []

    _log(f"등급 일괄 조회 시작: {len(cafe_urls)}개 카페")
    for i, url in enumerate(cafe_urls, 1):
        _log(f"[{i}/{len(cafe_urls)}] {url}")
        r = check_cafe_grade(driver, url, _log, save_to_sheet)
        results.append(r)

    ok = sum(1 for r in results if r["ok"])
    _log(f"등급 일괄 조회 완료: 성공 {ok}/{len(results)}")
    return results


def _save_grades_to_gsheet(cafe_url, grades, grade_info, _log):
    """등급 조회 결과를 구글시트에 기록."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    rows = []
    for g in grades:
        rows.append([
            ts,
            cafe_url,
            g["name"],
            g["level"],
            g["condition"],
            grade_info.get("my_grade_text", ""),
            "회원" if grade_info.get("is_member") else "미가입",
        ])

    if rows:
        result = func.append_to_gsheet(rows, sheet_name="등급조회", log_fn=_log)
        if result:
            _log(f"구글시트 기록 완료: {len(rows)}행")
        else:
            _log("구글시트 기록 실패")
