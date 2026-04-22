"""
네이버 카페 자동화 프로그램 (6종)
- 1순위: 카페 글쓰기 프로그램 (상세 GUI)
- 2~6순위: 탭/구조만 (미정)

SOFTCAT | SC-2026-0401-CF
"""

import sys
import os
import configparser
from datetime import datetime

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QTabWidget,
    QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QLineEdit, QPlainTextEdit,
    QComboBox, QSpinBox, QCheckBox, QGroupBox, QSlider,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QSplitter, QFrame, QFileDialog, QMessageBox,
    QProgressBar, QAbstractItemView, QScrollArea,
    QDialog
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QColor
import os
import func


# ─────────────────────────────────────────────
# 라이트모드 스타일
# ─────────────────────────────────────────────
STYLE_SHEET = """
QMainWindow {
    background-color: #f4f4f8;
}
QTabWidget::pane {
    border: 1px solid #c0c0cc;
    background-color: #f4f4f8;
    border-radius: 4px;
}
QTabBar::tab {
    background-color: #e0e0ea;
    color: #505060;
    padding: 8px 18px;
    margin-right: 2px;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    font-size: 13px;
    font-weight: bold;
    min-width: 120px;
}
QTabBar::tab:selected {
    background-color: #4a6cf7;
    color: #ffffff;
}
QTabBar::tab:hover:!selected {
    background-color: #d0d0dc;
    color: #303040;
}
QGroupBox {
    font-size: 13px;
    font-weight: bold;
    color: #303050;
    border: 1px solid #c0c0cc;
    border-radius: 6px;
    margin-top: 12px;
    padding-top: 18px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
}
QLabel {
    color: #303050;
    font-size: 12px;
}
QLineEdit, QPlainTextEdit, QComboBox, QSpinBox {
    background-color: #ffffff;
    color: #202030;
    border: 1px solid #b0b0c0;
    border-radius: 4px;
    padding: 5px 8px;
    font-size: 12px;
}
QSpinBox::up-button {
    width: 0; border: none;
}
QSpinBox::down-button {
    width: 0; border: none;
}
QSpinBox::up-arrow, QSpinBox::down-arrow {
    image: none; width: 0; height: 0;
}
QLineEdit:focus, QPlainTextEdit:focus {
    border: 1px solid #4a6cf7;
}
QComboBox::drop-down {
    border: none;
    width: 24px;
}
QComboBox QAbstractItemView {
    background-color: #ffffff;
    color: #202030;
    selection-background-color: #4a6cf7;
    selection-color: #ffffff;
}
QPushButton {
    background-color: #4a6cf7;
    color: #ffffff;
    border: none;
    border-radius: 4px;
    padding: 7px 16px;
    font-size: 12px;
    font-weight: bold;
}
QPushButton:hover {
    background-color: #5b7dff;
}
QPushButton:pressed {
    background-color: #3a5ce0;
}
QPushButton:disabled {
    background-color: #c0c0cc;
    color: #808090;
}
QPushButton[class="danger"] {
    background-color: #e53935;
}
QPushButton[class="danger"]:hover {
    background-color: #ef5350;
}
QPushButton[class="secondary"] {
    background-color: #e0e0ea;
    color: #404050;
}
QPushButton[class="secondary"]:hover {
    background-color: #d0d0dc;
}
QPushButton[class="success"] {
    background-color: #2e7d32;
}
QPushButton[class="success"]:hover {
    background-color: #388e3c;
}
QTableWidget {
    background-color: #ffffff;
    color: #202030;
    border: 1px solid #c0c0cc;
    gridline-color: #e0e0e8;
    border-radius: 4px;
    font-size: 12px;
    alternate-background-color: #f8f8fc;
}
QTableWidget::item {
    padding: 4px;
}
QTableWidget::item:selected {
    background-color: #4a6cf7;
    color: #ffffff;
}
QHeaderView::section {
    background-color: #eaeaf0;
    color: #404050;
    padding: 6px;
    border: 1px solid #d0d0d8;
    font-weight: bold;
    font-size: 11px;
}
QCheckBox {
    color: #303050;
    font-size: 12px;
    spacing: 6px;
}
QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border-radius: 3px;
    border: 1px solid #b0b0c0;
    background-color: #ffffff;
}
QCheckBox::indicator:checked {
    background-color: #4a6cf7;
    border-color: #4a6cf7;
}
QProgressBar {
    background-color: #e0e0ea;
    border: 1px solid #c0c0cc;
    border-radius: 4px;
    text-align: center;
    color: #303050;
    font-size: 11px;
    height: 20px;
}
QProgressBar::chunk {
    background-color: #4a6cf7;
    border-radius: 3px;
}
QStatusBar {
    background-color: #eaeaf0;
    color: #606070;
    font-size: 11px;
}
QSplitter::handle {
    background-color: #d0d0d8;
    width: 2px;
}
QScrollArea {
    background-color: transparent;
    border: none;
}
QScrollBar:vertical {
    background: #f0f0f4;
    width: 8px;
    border-radius: 4px;
}
QScrollBar::handle:vertical {
    background: #c0c0cc;
    border-radius: 4px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background: #a0a0b0;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
QSlider::groove:horizontal {
    height: 6px;
    background: #d0d0d8;
    border-radius: 3px;
}
QSlider::handle:horizontal {
    background: #4a6cf7;
    width: 16px;
    height: 16px;
    margin: -5px 0;
    border-radius: 8px;
    border: 2px solid #3a5ce0;
}
QSlider::handle:horizontal:hover {
    background: #5b7dff;
}
QSlider::sub-page:horizontal {
    background: #4a6cf7;
    border-radius: 3px;
}
"""


# ─────────────────────────────────────────────
# 슬라이더 위젯
# ─────────────────────────────────────────────
class LabeledSlider(QWidget):
    """슬라이더 + 값 표시"""
    def __init__(self, min_val=1, max_val=20, default=3, suffix=""):
        super().__init__()
        self.suffix = suffix
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(min_val, max_val)
        self.slider.setValue(default)
        self.slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        ti = 1 if (max_val - min_val) <= 20 else max(1, (max_val - min_val) // 10)
        self.slider.setTickInterval(ti)
        layout.addWidget(self.slider)

        self.label = QLabel(f"{default}{suffix}")
        self.label.setFixedWidth(36)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet("font-weight: bold; color: #4a6cf7;")
        layout.addWidget(self.label)

        self.slider.valueChanged.connect(lambda v: self.label.setText(f"{v}{suffix}"))

    def value(self):
        return self.slider.value()


class RangeSliderPair(QWidget):
    """최소~최대 범위 슬라이더 쌍"""
    def __init__(self, min_val, max_val, default_lo, default_hi, suffix=""):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self.slider_lo = QSlider(Qt.Orientation.Horizontal)
        self.slider_lo.setRange(min_val, max_val)
        self.slider_lo.setValue(default_lo)
        layout.addWidget(self.slider_lo)

        self.lbl_lo = QLabel(f"{default_lo}")
        self.lbl_lo.setFixedWidth(28)
        self.lbl_lo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_lo.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.lbl_lo)

        layout.addWidget(QLabel("~"))

        self.slider_hi = QSlider(Qt.Orientation.Horizontal)
        self.slider_hi.setRange(min_val, max_val)
        self.slider_hi.setValue(default_hi)
        layout.addWidget(self.slider_hi)

        self.lbl_hi = QLabel(f"{default_hi}")
        self.lbl_hi.setFixedWidth(28)
        self.lbl_hi.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_hi.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.lbl_hi)

        if suffix:
            layout.addWidget(QLabel(suffix))

        self.slider_lo.valueChanged.connect(lambda v: self.lbl_lo.setText(str(v)))
        self.slider_hi.valueChanged.connect(lambda v: self.lbl_hi.setText(str(v)))



# ─────────────────────────────────────────────
# 설정 탭
# ─────────────────────────────────────────────
class SettingsTab(QWidget):
    def __init__(self):
        super().__init__()
        self._init_ui()
        self._load_config()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # ── 프록시 설정 ──
        proxy_group = QGroupBox("프록시 설정")
        pg = QGridLayout(proxy_group)
        pg.addWidget(QLabel("프록시 파일:"), 0, 0)
        self.proxy_file_edit = QLineEdit()
        self.proxy_file_edit.setPlaceholderText("프록시 파일 경로 (IP:PORT 형식)")
        pg.addWidget(self.proxy_file_edit, 0, 1)
        btn_proxy = QPushButton("찾기")
        btn_proxy.setProperty("class", "secondary")
        btn_proxy.setFixedWidth(60)
        btn_proxy.clicked.connect(lambda: self._browse_file(self.proxy_file_edit, "텍스트 (*.txt)"))
        pg.addWidget(btn_proxy, 0, 2)
        layout.addWidget(proxy_group)

        # ── 구글시트 설정 ──
        gs_group = QGroupBox("구글시트 연동")
        gsg = QGridLayout(gs_group)
        gsg.addWidget(QLabel("서비스 계정 키:"), 0, 0)
        self.gs_sa_file = QLineEdit()
        self.gs_sa_file.setPlaceholderText("서비스 계정 JSON 키 파일 경로")
        gsg.addWidget(self.gs_sa_file, 0, 1)
        btn_sa = QPushButton("찾기")
        btn_sa.setProperty("class", "secondary")
        btn_sa.setFixedWidth(60)
        btn_sa.clicked.connect(lambda: self._browse_file(self.gs_sa_file, "JSON (*.json)"))
        gsg.addWidget(btn_sa, 0, 2)
        gsg.addWidget(QLabel("시트 ID:"), 1, 0)
        self.gs_sheet_id = QLineEdit()
        self.gs_sheet_id.setPlaceholderText("스프레드시트 ID (URL에서 /d/ 뒤의 값)")
        gsg.addWidget(self.gs_sheet_id, 1, 1)
        layout.addWidget(gs_group)

        # ── Gemini 설정 ──
        gemini_group = QGroupBox("Gemini AI 설정")
        gg = QGridLayout(gemini_group)
        gg.addWidget(QLabel("API 키:"), 0, 0)
        self.gemini_api_key = QLineEdit()
        self.gemini_api_key.setPlaceholderText("Gemini API 키")
        self.gemini_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        gg.addWidget(self.gemini_api_key, 0, 1)
        gg.addWidget(QLabel("모델:"), 1, 0)
        self.gemini_model = QComboBox()
        self.gemini_model.addItems(["gemini-2.5-pro", "gemini-2.5-flash"])
        gg.addWidget(self.gemini_model, 1, 1)
        layout.addWidget(gemini_group)

        # ── 2Captcha 설정 ──
        captcha_group = QGroupBox("2Captcha 설정 (카페 가입 캡차)")
        cg2 = QGridLayout(captcha_group)
        cg2.addWidget(QLabel("API 키:"), 0, 0)
        self.twocaptcha_api_key = QLineEdit()
        self.twocaptcha_api_key.setPlaceholderText("2Captcha API 키")
        self.twocaptcha_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        cg2.addWidget(self.twocaptcha_api_key, 0, 1)
        layout.addWidget(captcha_group)

        # ── 하이아이피 설정 ──
        # (삭제됨 — 필요 없음)

        # ── 저장 버튼 ──
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_save = QPushButton("💾  설정 저장")
        btn_save.setMinimumHeight(38)
        btn_save.setMinimumWidth(150)
        btn_save.clicked.connect(self._save_config)
        btn_layout.addWidget(btn_save)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        layout.addStretch()

    def _browse_file(self, target, filt="모든 파일 (*.*)"):
        path, _ = QFileDialog.getOpenFileName(self, "파일 선택", "", filt)
        if path:
            target.setText(path)

    def _config_path(self):
        return func.CONFIG_PATH

    def _load_config(self):
        cfg = configparser.ConfigParser()
        cfg.read(self._config_path(), encoding="utf-8")
        self.gs_sa_file.setText(cfg.get("google_sheets", "sa_file", fallback=""))
        self.gs_sheet_id.setText(cfg.get("google_sheets", "sheet_id", fallback=""))
        self.gemini_api_key.setText(cfg.get("gemini", "api_key", fallback=""))
        self.twocaptcha_api_key.setText(cfg.get("2captcha", "api_key", fallback=""))
        self.proxy_file_edit.setText(cfg.get("paths", "proxy_file", fallback=""))

    def _save_config(self):
        cfg = configparser.ConfigParser()
        cfg["gemini"] = {"api_key": self.gemini_api_key.text()}
        cfg["2captcha"] = {"api_key": self.twocaptcha_api_key.text()}
        cfg["google_sheets"] = {"sa_file": self.gs_sa_file.text(), "sheet_id": self.gs_sheet_id.text()}
        cfg["paths"] = {"proxy_file": self.proxy_file_edit.text()}
        with open(self._config_path(), "w", encoding="utf-8") as f:
            cfg.write(f)
        QMessageBox.information(self, "저장 완료", "설정이 config.ini에 저장되었습니다.")

# ─────────────────────────────────────────────

# ─────────────────────────────────────────────
# 로그인 워커 스레드
# ─────────────────────────────────────────────
class LoginWorkerThread(QThread):
    """워커별 계정 순차 처리 스레드. 로그인은 글로벌 락, 카페 작업은 병렬."""
    log_signal = pyqtSignal(str)
    worker_update = pyqtSignal(int, str)  # idx, status
    finished_signal = pyqtSignal(list)  # results

    def __init__(self, worker_assignments, proxies, settings=None):
        """
        worker_assignments: [{worker_idx, accounts: [{id,pw,...,tasks:[...]},...]}]
        proxies: 전체 프록시 리스트
        """
        super().__init__()
        self.worker_assignments = worker_assignments
        self.proxies = proxies
        self.settings = settings or {}
        self.results = []
        self._stop_flag = False
        self._pause_flag = False
        self._login_lock = None
        self.work_stats = {"reply_ok": 0, "reply_fail": 0, "write_ok": 0, "write_fail": 0, "suspended": 0, "not_member": 0}
        self.used_manuscripts = set()  # 사용된 원고 폴더 경로

    def stop(self):
        self._stop_flag = True
        self._pause_flag = False

    def pause(self):
        self._pause_flag = True

    def resume(self):
        self._pause_flag = False

    def _wait_if_paused(self):
        import time as _time
        while self._pause_flag and not self._stop_flag:
            _time.sleep(0.5)

    def run(self):
        import concurrent.futures, threading, shutil, tempfile, glob

        self._login_lock = threading.Lock()
        cafe_grades = {}
        cafe_grades_lock = threading.Lock()

        # 임시 폴더 정리
        tmp = tempfile.gettempdir()
        for d in glob.glob(os.path.join(tmp, "uc_worker_*")):
            try:
                shutil.rmtree(d, ignore_errors=True)
            except:
                pass
        self.log_signal.emit("임시 폴더 정리 완료")

        num_workers = len(self.worker_assignments)
        self.log_signal.emit(f"=== 워커 {num_workers}개 시작 ===")

        # ── 1라운드: 순차 로그인 → 동시 작업 ──
        self.log_signal.emit("=== 1라운드: 순차 로그인 ===")
        first_round_drivers = {}  # {worker_idx: (driver, grp)}

        for w in self.worker_assignments:
            if self._stop_flag:
                break
            self._wait_if_paused()

            worker_idx = w["worker_idx"]
            if not w["accounts"]:
                continue
            grp = w["accounts"][0]
            proxy = w["proxies"][0] if w["proxies"] else ""
            nid = grp["id"]

            self.log_signal.emit(f"워커#{worker_idx+1} 프록시={proxy} / ID={nid} (1/{len(w['accounts'])})")
            self.worker_update.emit(worker_idx, f"로그인 중: {nid}")

            driver = None
            try:
                driver = func.create_driver(proxy, worker_idx)
                log_fn = lambda msg, _w=worker_idx: self.log_signal.emit(f"  워커#{_w+1} {msg}")
                result = func.naver_login(driver, grp, log_fn)
                result["worker"] = worker_idx
                result["id"] = nid
                self.results.append(result)

                if result["ok"]:
                    self.log_signal.emit(f"워커#{worker_idx+1} [성공] [{nid}] {result['msg']}")
                    self.worker_update.emit(worker_idx, f"로그인 성공: {nid}")
                    first_round_drivers[worker_idx] = (driver, grp, w)
                elif result.get("error") == "needs_protection":
                    # 보호조치 감지 — 1라운드에서는 해제 시도 (순차이므로 OK)
                    self.log_signal.emit(f"워커#{worker_idx+1} [{nid}] 보호조치 감지 → 해제 시도")
                    self.worker_update.emit(worker_idx, f"보호조치 해제: {nid}")
                    prot_result = func._handle_protection(driver, grp, result.get("url", ""), result.get("page", ""), log_fn)
                    if prot_result and prot_result.get("ok"):
                        self.log_signal.emit(f"워커#{worker_idx+1} [성공] [{nid}] {prot_result['msg']}")
                        self.worker_update.emit(worker_idx, f"로그인 성공: {nid}")
                        prot_result["worker"] = worker_idx
                        prot_result["id"] = nid
                        self.results.append(prot_result)
                        first_round_drivers[worker_idx] = (driver, grp, w)
                    else:
                        msg = prot_result["msg"] if prot_result else "보호조치 해제 실패"
                        self.log_signal.emit(f"워커#{worker_idx+1} [실패] [{nid}] {msg}")
                        self.worker_update.emit(worker_idx, f"로그인 실패: {nid}")
                        self.results.append(prot_result or {"ok": False, "msg": msg, "error": "blocked_unknown", "worker": worker_idx, "id": nid})
                        self._record_login_fail(grp, msg, log_fn)
                        try:
                            driver.quit()
                        except:
                            pass
                        self._cleanup_worker_dir(worker_idx)
                else:
                    self.log_signal.emit(f"워커#{worker_idx+1} [실패] [{nid}] {result['msg']}")
                    self.worker_update.emit(worker_idx, f"로그인 실패: {nid}")
                    self._record_login_fail(grp, result['msg'], log_fn)
                    try:
                        driver.quit()
                    except:
                        pass
                    self._cleanup_worker_dir(worker_idx)
            except Exception as e:
                self.log_signal.emit(f"워커#{worker_idx+1} [실패] [{nid}] {str(e)[:60]}")
                self.worker_update.emit(worker_idx, f"에러: {nid}")
                self.results.append({"ok": False, "msg": str(e)[:60], "error": "exception", "worker": worker_idx, "id": nid})
                self._record_login_fail(grp, str(e)[:60], log_fn)
                if driver:
                    try:
                        driver.quit()
                    except:
                        pass
                self._cleanup_worker_dir(worker_idx)

        ok_count = len(first_round_drivers)
        total_count = len(self.results)
        self.log_signal.emit(f"=== 1라운드 로그인 완료: 성공 {ok_count}/{total_count} ===")

        if self._stop_flag:
            self.log_signal.emit("=== 전체 작업 완료 ===")
            self.finished_signal.emit(self.results)
            return

        # ── 1라운드 카페 작업 (병렬) + 2라운드~ 워커별 자율 ──
        self.log_signal.emit(f"=== 카페 작업 시작 (워커 {num_workers}개) ===")

        def worker_loop(worker_idx, driver, first_grp, assignment):
            """1라운드 카페 작업 + 2라운드~ 로그인+작업 반복."""
            account_list = assignment["accounts"]
            proxy_list = assignment["proxies"]
            start_idx = 1  # 2라운드 시작 인덱스 (첫 번째는 1라운드에서 처리)

            # 1라운드: 로그인 성공한 경우만 카페 작업
            if driver and first_grp:
                self._do_account_work(worker_idx, driver, first_grp, cafe_grades, cafe_grades_lock)
                self.log_signal.emit(f"워커#{worker_idx+1} [{first_grp['id']}] 작업 완료 → 브라우저 종료")
                try:
                    driver.quit()
                except:
                    pass
                self._cleanup_worker_dir(worker_idx)

            # 2라운드~: 나머지 계정 순차 처리
            for acc_idx in range(start_idx, len(account_list)):
                if self._stop_flag:
                    break
                self._wait_if_paused()

                grp = account_list[acc_idx]
                proxy = proxy_list[acc_idx % len(proxy_list)] if proxy_list else ""
                nid = grp["id"]

                # 로그인 (글로벌 락)
                self.worker_update.emit(worker_idx, f"로그인 대기: {nid}")
                with self._login_lock:
                    if self._stop_flag:
                        break
                    self.log_signal.emit(f"워커#{worker_idx+1} 프록시={proxy} / ID={nid} ({acc_idx+1}/{len(account_list)})")
                    self.worker_update.emit(worker_idx, f"로그인 중: {nid}")

                    drv = None
                    login_ok = False
                    needs_prot = False
                    prot_data = None
                    try:
                        drv = func.create_driver(proxy, worker_idx)
                        log_fn = lambda msg, _w=worker_idx: self.log_signal.emit(f"  워커#{_w+1} {msg}")
                        result = func.naver_login(drv, grp, log_fn)
                        result["worker"] = worker_idx
                        result["id"] = nid
                        self.results.append(result)

                        if result["ok"]:
                            self.log_signal.emit(f"워커#{worker_idx+1} [성공] [{nid}] {result['msg']}")
                            self.worker_update.emit(worker_idx, f"로그인 성공: {nid}")
                            login_ok = True
                        elif result.get("error") == "needs_protection":
                            needs_prot = True
                            prot_data = result
                        else:
                            self.log_signal.emit(f"워커#{worker_idx+1} [실패] [{nid}] {result['msg']}")
                            self.worker_update.emit(worker_idx, f"로그인 실패: {nid}")
                            log_fn = lambda msg, _w=worker_idx: self.log_signal.emit(f"  워커#{_w+1} {msg}")
                            self._record_login_fail(grp, result['msg'], log_fn)
                            try:
                                drv.quit()
                            except:
                                pass
                            self._cleanup_worker_dir(worker_idx)
                            continue
                    except Exception as e:
                        self.log_signal.emit(f"워커#{worker_idx+1} [실패] [{nid}] {str(e)[:60]}")
                        self.worker_update.emit(worker_idx, f"에러: {nid}")
                        self.results.append({"ok": False, "msg": str(e)[:60], "error": "exception", "worker": worker_idx, "id": nid})
                        log_fn = lambda msg, _w=worker_idx: self.log_signal.emit(f"  워커#{_w+1} {msg}")
                        self._record_login_fail(grp, str(e)[:60], log_fn)
                        if drv:
                            try:
                                drv.quit()
                            except:
                                pass
                        self._cleanup_worker_dir(worker_idx)
                        continue

                # 보호조치 해제 (락 밖 — 다른 워커 로그인 안 막음)
                if needs_prot:
                    self.log_signal.emit(f"워커#{worker_idx+1} [{nid}] 보호조치 감지 → 해제 시도")
                    self.worker_update.emit(worker_idx, f"보호조치 해제: {nid}")
                    log_fn = lambda msg, _w=worker_idx: self.log_signal.emit(f"  워커#{_w+1} {msg}")
                    prot_result = func._handle_protection(drv, grp, prot_data.get("url", ""), prot_data.get("page", ""), log_fn)
                    if prot_result and prot_result.get("ok"):
                        self.log_signal.emit(f"워커#{worker_idx+1} [성공] [{nid}] {prot_result['msg']}")
                        login_ok = True
                    else:
                        msg = prot_result["msg"] if prot_result else "보호조치 해제 실패"
                        self.log_signal.emit(f"워커#{worker_idx+1} [실패] [{nid}] {msg}")
                        self.worker_update.emit(worker_idx, f"로그인 실패: {nid}")
                        self._record_login_fail(grp, msg, log_fn)
                        try:
                            drv.quit()
                        except:
                            pass
                        self._cleanup_worker_dir(worker_idx)
                        continue

                if not login_ok:
                    continue

                # 카페 작업 (락 밖)
                self._do_account_work(worker_idx, drv, grp, cafe_grades, cafe_grades_lock)

                # 브라우저 종료
                self.log_signal.emit(f"워커#{worker_idx+1} [{nid}] 작업 완료 → 브라우저 종료")
                try:
                    drv.quit()
                except:
                    pass
                self._cleanup_worker_dir(worker_idx)

            self.worker_update.emit(worker_idx, f"전체 완료 ({len(account_list)}개 계정)")
            self.log_signal.emit(f"워커#{worker_idx+1} 전체 완료")

        with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as pool:
            futures = []
            for w in self.worker_assignments:
                w_idx = w["worker_idx"]
                if w_idx in first_round_drivers:
                    drv, grp, assignment = first_round_drivers[w_idx]
                    futures.append(pool.submit(worker_loop, w_idx, drv, grp, assignment))
                else:
                    # 1라운드 실패 워커 — driver=None, first_grp=None
                    futures.append(pool.submit(worker_loop, w_idx, None, None, w))
            concurrent.futures.wait(futures)

        self.log_signal.emit("=== 전체 작업 완료 ===")
        self.finished_signal.emit(self.results)

    def _cleanup_worker_dir(self, worker_idx):
        import shutil as _shutil, tempfile as _tf
        try:
            _shutil.rmtree(os.path.join(_tf.gettempdir(), f"uc_worker_{worker_idx}"), ignore_errors=True)
        except:
            pass

    def _do_account_work(self, worker_idx, driver, grp, cafe_grades, cafe_grades_lock):
        """한 계정의 카페 작업 수행."""
        nid = grp["id"]
        log_fn = lambda msg, _w=worker_idx: self.log_signal.emit(f"  워커#{_w+1} {msg}")
        tasks = grp.get("tasks", [])
        success_urls = []

        for t_idx, task in enumerate(tasks):
            if self._stop_flag:
                break
            self._wait_if_paused()

            cafe_url = task.get("cafe_url", "")
            if not cafe_url:
                continue

            cafe_short = cafe_url.replace("https://cafe.naver.com/", "")
            self.worker_update.emit(worker_idx, f"카페: {cafe_short} ({t_idx+1}/{len(tasks)})")
            self.log_signal.emit(f"워커#{worker_idx+1} [{nid}] 카페 접속: {cafe_short}")

            try:
                acc_for_task = {**grp, **task}
                cafe_result = func.visit_cafe(driver, acc_for_task, log_fn)

                if cafe_result.get("ok"):
                    need_grade = False
                    with cafe_grades_lock:
                        if cafe_url not in cafe_grades:
                            cafe_grades[cafe_url] = None
                            need_grade = True
                    if need_grade:
                        self.log_signal.emit(f"워커#{worker_idx+1} [{nid}] 등급 조회: {cafe_short}")
                        gi = func.get_cafe_grades(driver, cafe_url, log_fn)
                        with cafe_grades_lock:
                            cafe_grades[cafe_url] = gi
                    else:
                        for _ in range(30):
                            with cafe_grades_lock:
                                if cafe_grades.get(cafe_url) is not None:
                                    break
                            import time as _time
                            _time.sleep(1)

                    self.worker_update.emit(worker_idx, f"작업 중: {cafe_short}")
                    work_result = func.do_cafe_work(driver, acc_for_task, cafe_grades, self.settings, log_fn)
                    self.log_signal.emit(f"워커#{worker_idx+1} [{nid}] {cafe_short}: {work_result['msg']}")

                    if work_result.get("error") == "suspended":
                        self.worker_update.emit(worker_idx, f"활동정지: {nid} ({cafe_short})")
                        self.work_stats["suspended"] += 1
                        self._record_result(grp, cafe_url, task, "", "실패", f"활동정지({cafe_short})", log_fn)
                        self.log_signal.emit(f"워커#{worker_idx+1} [{nid}] {cafe_short} 활동정지 → 다음 카페로 진행")
                        continue

                    self._record_work_rows(worker_idx, nid, cafe_short, work_result, log_fn)
                    for r in work_result.get("result_rows", []):
                        if r.get("status") == "성공" and r.get("url"):
                            success_urls.append(r["url"])

                elif cafe_result.get("need_join"):
                    self.log_signal.emit(f"워커#{worker_idx+1} [{nid}] {cafe_short}: 미가입 → 자동가입")
                    self.worker_update.emit(worker_idx, f"자동가입: {cafe_short}")
                    from cafe_join import join_cafe
                    join_result = join_cafe(driver, cafe_url, log_fn=log_fn)
                    self.log_signal.emit(f"워커#{worker_idx+1} [{nid}] {cafe_short}: {join_result['msg']}")

                    if not join_result.get("ok"):
                        self.work_stats["not_member"] += 1
                        self._record_result(grp, cafe_url, task, "", "실패", join_result.get("msg", "가입실패"), log_fn)
                        continue

                    self.log_signal.emit(f"워커#{worker_idx+1} [{nid}] {cafe_short}: 가입 성공 → 작업")
                    with cafe_grades_lock:
                        if cafe_url not in cafe_grades:
                            cafe_grades[cafe_url] = func.get_cafe_grades(driver, cafe_url, log_fn)
                    work_result = func.do_cafe_work(driver, acc_for_task, cafe_grades, self.settings, log_fn)
                    self.log_signal.emit(f"워커#{worker_idx+1} [{nid}] {cafe_short}: {work_result['msg']}")
                    self._record_work_rows(worker_idx, nid, cafe_short, work_result, log_fn)
                    for r in work_result.get("result_rows", []):
                        if r.get("status") == "성공" and r.get("url"):
                            success_urls.append(r["url"])
                else:
                    self.log_signal.emit(f"워커#{worker_idx+1} [{nid}] {cafe_short}: {cafe_result['msg']}")
            except Exception as ce:
                self.log_signal.emit(f"워커#{worker_idx+1} [{nid}] {cafe_short} 에러: {str(ce)[:60]}")

        # 모든 카페 작업 완료 후 삭제 유무 체크
        if success_urls:
            self.log_signal.emit(f"워커#{worker_idx+1} [{nid}] 삭제 유무 체크: {len(success_urls)}건")
            self.worker_update.emit(worker_idx, f"삭제체크: {nid}")
            url_status = {}
            for url in success_urls:
                status = func.check_post_deleted(driver, url, log_fn)
                url_status[url] = status
                self.log_signal.emit(f"  워커#{worker_idx+1} [{nid}] {url[:50]} → {status}")
            func.update_gsheet_deleted(url_status, log_fn=log_fn)
            self.log_signal.emit(f"워커#{worker_idx+1} [{nid}] 삭제 유무 체크 완료")

    def _record_result(self, grp, cafe_url, task, url, status, error, log_fn):
        from datetime import datetime as _dt
        func.append_to_gsheet_with_color([[
            grp.get("id", ""), grp.get("pw", ""), grp.get("name", ""),
            grp.get("birth", ""), grp.get("gender", ""),
            cafe_url, task.get("menu_id", ""), url, "", "",
            _dt.now().strftime("%Y-%m-%d %H:%M:%S"), status, error
        ]], sheet_name="결과값", log_fn=log_fn)

    def _record_login_fail(self, grp, error_msg, log_fn):
        """로그인 실패한 계정의 모든 카페 작업을 결과값에 실패로 기록."""
        from datetime import datetime as _dt
        tasks = grp.get("tasks", [])
        if not tasks:
            tasks = [{"cafe_url": "", "menu_id": ""}]
        rows = []
        for task in tasks:
            for _ in range(task.get("post_count", 1)):
                rows.append([
                    grp.get("id", ""), grp.get("pw", ""), grp.get("name", ""),
                    grp.get("birth", ""), grp.get("gender", ""),
                    task.get("cafe_url", ""), task.get("menu_id", ""),
                    "", "", "",
                    _dt.now().strftime("%Y-%m-%d %H:%M:%S"), "실패", error_msg
                ])
        if rows:
            func.append_to_gsheet_with_color(rows, sheet_name="결과값", log_fn=log_fn)

    def _record_work_rows(self, worker_idx, nid, cafe_short, work_result, log_fn):
        rows = work_result.get("result_rows", [])
        if rows:
            self.log_signal.emit(f"워커#{worker_idx+1} [{nid}] 결과시트 기록: {len(rows)}행")
            from datetime import datetime as _dt
            sheet_rows = []
            for r in rows:
                sheet_rows.append([
                    r.get("id", ""), r.get("pw", ""), r.get("name", ""),
                    r.get("birth", ""), r.get("gender", ""),
                    r.get("cafe_url", ""), r.get("menu_id", ""),
                    r.get("url", ""), r.get("deleted", "미확인"),
                    r.get("manuscript", ""),
                    _dt.now().strftime("%Y-%m-%d %H:%M:%S"),
                    r.get("status", ""), r.get("error", ""),
                ])
            func.append_to_gsheet_with_color(sheet_rows, sheet_name="결과값", log_fn=log_fn)
            for r in rows:
                if r.get("status") == "성공":
                    self.work_stats["reply_ok"] += 1
                    # 사용된 원고 추적
                    ms_name = r.get("manuscript", "")
                    if ms_name:
                        self.used_manuscripts.add(ms_name)
                else:
                    self.work_stats["reply_fail"] += 1
            self.worker_update.emit(worker_idx, f"완료: {cafe_short}")
        else:
            self.log_signal.emit(f"워커#{worker_idx+1} [{nid}] {cafe_short}: 작성된 글 없음")

# 1순위: 카페 글쓰기 탭 (좌우 스플리터 구조 유지)
# ─────────────────────────────────────────────
class CafeWriterTab(QWidget):
    def __init__(self):
        super().__init__()
        self._init_ui()

    def _init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # ══════════════════════════════════
        # 좌측: 설정 패널
        # ══════════════════════════════════
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)

        # ── 워커 설정 ──
        worker_group = QGroupBox("워커 설정")
        wkg = QGridLayout(worker_group)
        wkg.addWidget(QLabel("워커 수:"), 0, 0)
        self.worker_slider = LabeledSlider(1, 50, 50)
        wkg.addWidget(self.worker_slider, 0, 1, 1, 2)
        left_layout.addWidget(worker_group)

        # ── 원고 폴더 ──
        content_group = QGroupBox("원고 관리")
        cg = QVBoxLayout(content_group)

        # 폴더 선택 행
        folder_row = QHBoxLayout()
        folder_row.addWidget(QLabel("원고 대폴더:"))
        self.content_folder = QLineEdit()
        self.content_folder.setPlaceholderText("대폴더 경로 (소폴더들이 들어있는 상위 폴더)")
        folder_row.addWidget(self.content_folder)
        btn_folder = QPushButton("폴더 선택")
        btn_folder.setProperty("class", "secondary")
        btn_folder.setFixedWidth(80)
        btn_folder.clicked.connect(self._browse_folder)
        folder_row.addWidget(btn_folder)
        self.lbl_content_count = QLabel("원고: 0개")
        self.lbl_content_count.setStyleSheet("color: #606070; font-weight: bold;")
        folder_row.addWidget(self.lbl_content_count)
        cg.addLayout(folder_row)

        # 소폴더(원고) 리스트 테이블
        self.manuscript_table = QTableWidget(0, 4)
        self.manuscript_table.setHorizontalHeaderLabels(["키워드(폴더명)", "txt", "이미지", "경로"])
        mh = self.manuscript_table.horizontalHeader()
        mh.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        mh.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        mh.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        mh.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.manuscript_table.setColumnWidth(1, 40)
        self.manuscript_table.setColumnWidth(2, 50)
        self.manuscript_table.setMaximumHeight(180)
        self.manuscript_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.manuscript_table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.manuscript_table.setAlternatingRowColors(True)
        self.manuscript_table.cellClicked.connect(self._on_manuscript_row_clicked)
        self._selected_ms_rows = set()
        cg.addWidget(self.manuscript_table)

        # 삭제 버튼
        ms_btn_row = QHBoxLayout()
        btn_del_ms = QPushButton("선택 원고 삭제")
        btn_del_ms.setProperty("class", "danger")
        btn_del_ms.setFixedWidth(120)
        btn_del_ms.clicked.connect(self._delete_selected_manuscripts)
        ms_btn_row.addWidget(btn_del_ms)
        btn_select_all = QPushButton("전체 선택")
        btn_select_all.setProperty("class", "secondary")
        btn_select_all.setFixedWidth(80)
        btn_select_all.clicked.connect(self._select_all_manuscripts)
        ms_btn_row.addWidget(btn_select_all)
        ms_btn_row.addStretch()
        cg.addLayout(ms_btn_row)

        left_layout.addWidget(content_group)

        # ── 글쓰기 설정 ──
        write_group = QGroupBox("글쓰기 설정")
        wg = QGridLayout(write_group)

        wg.addWidget(QLabel("작성 모드:"), 0, 0)
        self.write_mode = QComboBox()
        self.write_mode.addItems(["글쓰기", "답글", "글쓰기 + 답글"])
        self.write_mode.setCurrentIndex(1)
        wg.addWidget(self.write_mode, 0, 1, 1, 2)

        wg.addWidget(QLabel("페이지 범위:"), 1, 0)
        page_range_layout = QHBoxLayout()
        self.page_lo = QSpinBox()
        self.page_lo.setRange(1, 9999)
        self.page_lo.setValue(1)
        page_range_layout.addWidget(self.page_lo)
        lbl_p_tilde = QLabel("~")
        lbl_p_tilde.setFixedWidth(20)
        lbl_p_tilde.setAlignment(Qt.AlignmentFlag.AlignCenter)
        page_range_layout.addWidget(lbl_p_tilde)
        self.page_hi = QSpinBox()
        self.page_hi.setRange(1, 9999)
        self.page_hi.setValue(10)
        page_range_layout.addWidget(self.page_hi)
        lbl_p_unit = QLabel("")
        lbl_p_unit.setFixedWidth(20)
        page_range_layout.addWidget(lbl_p_unit)
        wg.addLayout(page_range_layout, 1, 1, 1, 2)

        wg.addWidget(QLabel("딜레이(초):"), 2, 0)
        delay_range_layout = QHBoxLayout()
        self.delay_lo = QSpinBox()
        self.delay_lo.setRange(1, 600)
        self.delay_lo.setValue(3)
        delay_range_layout.addWidget(self.delay_lo)
        lbl_d_tilde = QLabel("~")
        lbl_d_tilde.setFixedWidth(20)
        lbl_d_tilde.setAlignment(Qt.AlignmentFlag.AlignCenter)
        delay_range_layout.addWidget(lbl_d_tilde)
        self.delay_hi = QSpinBox()
        self.delay_hi.setRange(1, 600)
        self.delay_hi.setValue(8)
        delay_range_layout.addWidget(self.delay_hi)
        lbl_d_unit = QLabel("초")
        lbl_d_unit.setFixedWidth(20)
        delay_range_layout.addWidget(lbl_d_unit)
        wg.addLayout(delay_range_layout, 2, 1, 1, 2)

        self.chk_allow_comment = QCheckBox("댓글허용")
        self.chk_allow_comment.setChecked(True)
        wg.addWidget(self.chk_allow_comment, 3, 0)

        self.chk_allow_search = QCheckBox("검색허용")
        self.chk_allow_search.setChecked(True)
        wg.addWidget(self.chk_allow_search, 3, 1)

        self.chk_public = QCheckBox("전체공개")
        self.chk_public.setChecked(True)
        wg.addWidget(self.chk_public, 3, 2)

        # 전체공개 체크 시 검색허용 강제 체크+비활성화
        self.chk_public.toggled.connect(self._on_public_toggled)
        self._on_public_toggled(True)  # 초기 상태 반영

        self.chk_delete_images = QCheckBox("작성 후 원본 사진 삭제")
        self.chk_delete_images.setChecked(False)
        wg.addWidget(self.chk_delete_images, 4, 0, 1, 3)

        left_layout.addWidget(write_group)

        # ── 답글 등급 ──
        grade_group = QGroupBox("답글 등급 필터")
        grade_layout = QVBoxLayout(grade_group)
        grade_row = QHBoxLayout()
        self.grade_checks = {}
        for name in ["탈퇴회원", "0단계", "1단계", "2단계", "3단계", "4단계", "5단계"]:
            cb = QCheckBox(name)
            cb.setChecked(True)
            self.grade_checks[name] = cb
            grade_row.addWidget(cb)
        grade_row.addStretch()
        grade_layout.addLayout(grade_row)

        left_layout.addWidget(grade_group)

        # ── 카페 설정 ──
        cafe_opt_group = QGroupBox("카페 설정")
        cog = QVBoxLayout(cafe_opt_group)
        self.chk_auto_join = QCheckBox("카페 미가입 시 자동 가입")
        self.chk_auto_join.setChecked(True)
        cog.addWidget(self.chk_auto_join)
        self.chk_grade_check = QCheckBox("등급 체크 후 글쓰기 (게시판 자동 탐색)")
        self.chk_grade_check.setChecked(True)
        cog.addWidget(self.chk_grade_check)
        left_layout.addWidget(cafe_opt_group)

        # 왼쪽 패널을 스크롤 영역으로 감싸기
        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setWidget(left_panel)
        left_scroll.setFrameShape(QFrame.Shape.NoFrame)
        left_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        left_scroll.setMinimumWidth(420)

        # ══════════════════════════════════
        # 우측: 실행 / 모니터링 패널
        # ══════════════════════════════════
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(8)

        # ── 실행 컨트롤 ──
        ctrl_group = QGroupBox("실행 제어")
        ctrl_layout = QHBoxLayout(ctrl_group)

        self.btn_start = QPushButton("▶  시작")
        self.btn_start.setProperty("class", "success")
        self.btn_start.setMinimumHeight(38)
        self.btn_start.clicked.connect(self._on_start)
        ctrl_layout.addWidget(self.btn_start)

        self.btn_pause = QPushButton("⏸  일시정지")
        self.btn_pause.setEnabled(False)
        self.btn_pause.setMinimumHeight(38)
        self.btn_pause.clicked.connect(self._on_pause)
        ctrl_layout.addWidget(self.btn_pause)

        self.btn_stop = QPushButton("⏹  중지")
        self.btn_stop.setProperty("class", "danger")
        self.btn_stop.setEnabled(False)
        self.btn_stop.setMinimumHeight(38)
        self.btn_stop.clicked.connect(self._on_stop)
        ctrl_layout.addWidget(self.btn_stop)

        right_layout.addWidget(ctrl_group)

        # ── 워커 상태 테이블 ──
        worker_group = QGroupBox("워커 상태 모니터링")
        worker_layout = QVBoxLayout(worker_group)

        self.worker_table = QTableWidget(0, 6)
        self.worker_table.setHorizontalHeaderLabels([
            "워커#", "계정", "프록시", "카페", "게시판", "상태"
        ])
        header = self.worker_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.worker_table.setColumnWidth(0, 50)
        self.worker_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.worker_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.worker_table.setAlternatingRowColors(True)
        worker_layout.addWidget(self.worker_table)

        # 요약
        summary_layout = QVBoxLayout()
        self.lbl_summary = QLabel("로그인: 성공 0 | 생년월일 0 | 핸드폰 0 | 영구정지 0 | 캡차 0 | 보안인증 0 | 실패 0 / 총 0개")
        self.lbl_summary.setFont(QFont("Malgun Gothic", 11, QFont.Weight.Bold))
        self.lbl_summary.setStyleSheet("color: #303050;")
        summary_layout.addWidget(self.lbl_summary)
        self.lbl_work_summary = QLabel("작업: 답글성공 0 | 답글실패 0 | 글쓰기성공 0 | 글쓰기실패 0 | 활동정지 0 | 미가입 0")
        self.lbl_work_summary.setFont(QFont("Malgun Gothic", 11, QFont.Weight.Bold))
        self.lbl_work_summary.setStyleSheet("color: #303050;")
        summary_layout.addWidget(self.lbl_work_summary)
        summary_layout.addStretch()
        worker_layout.addLayout(summary_layout)

        right_layout.addWidget(worker_group)

        # ── 로그 ──
        log_group = QGroupBox("결과 로그")
        log_layout = QVBoxLayout(log_group)

        self.log_area = QPlainTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setMaximumBlockCount(1000)
        self.log_area.setFont(QFont("Malgun Gothic", 10))
        self.log_area.setStyleSheet(
            "background-color: #fafafa; color: #202030; border: 1px solid #c0c0cc;"
        )
        log_layout.addWidget(self.log_area)

        log_btn_layout = QHBoxLayout()
        btn_clear = QPushButton("로그 지우기")
        btn_clear.setProperty("class", "secondary")
        btn_clear.clicked.connect(self.log_area.clear)
        log_btn_layout.addWidget(btn_clear)
        btn_export = QPushButton("로그 내보내기")
        btn_export.setProperty("class", "secondary")
        btn_export.clicked.connect(self._export_log)
        log_btn_layout.addWidget(btn_export)
        log_btn_layout.addStretch()
        log_layout.addLayout(log_btn_layout)

        right_layout.addWidget(log_group)

        # 스플리터 조립
        splitter.addWidget(left_scroll)
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 6)

        main_layout.addWidget(splitter)

        self._log("카페 글쓰기 프로그램 초기화 완료")
        self._log("계정 파일과 프록시를 설정한 후 시작하세요.")

    # ── 유틸 ──
    def _on_public_toggled(self, checked):
        """전체공개 체크 시 검색허용 강제 체크+비활성화."""
        if checked:
            self.chk_allow_search.setChecked(True)
            self.chk_allow_search.setEnabled(False)
        else:
            self.chk_allow_search.setEnabled(True)

    def _export_log(self):
        """로그를 txt 파일로 내보내기."""
        from datetime import datetime
        default_name = f"로그_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        path, _ = QFileDialog.getSaveFileName(self, "로그 내보내기", default_name, "텍스트 (*.txt)")
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self.log_area.toPlainText())
            self._log(f"로그 내보내기 완료: {path}")

    def _browse_file(self, target, filt="모든 파일 (*.*)"):
        path, _ = QFileDialog.getOpenFileName(self, "파일 선택", "", filt)
        if path:
            target.setText(path)

    def _browse_folder(self):
        path = QFileDialog.getExistingDirectory(self, "원고 폴더 선택 (여러 번 추가 가능)")
        if path:
            self.content_folder.setText(path)
            items = func.get_manuscript_display_list(path)
            for item in items:
                row = self.manuscript_table.rowCount()
                self.manuscript_table.insertRow(row)
                self.manuscript_table.setItem(row, 0, QTableWidgetItem(item["name"]))
                self.manuscript_table.setItem(row, 1, QTableWidgetItem(str(item["txt_count"])))
                self.manuscript_table.setItem(row, 2, QTableWidgetItem(str(item["img_count"])))
                self.manuscript_table.setItem(row, 3, QTableWidgetItem(item["path"]))
            total = self.manuscript_table.rowCount()
            self.lbl_content_count.setText(f"원고: {total}개")
            self._log(f"원고 폴더 추가: {len(items)}개 → 총 {total}개")

    def _delete_selected_manuscripts(self):
        """선택된(연빨강) 원고 삭제."""
        rows_to_delete = sorted(self._selected_ms_rows, reverse=True)
        for r in rows_to_delete:
            self.manuscript_table.removeRow(r)
        self._selected_ms_rows.clear()
        total = self.manuscript_table.rowCount()
        self.lbl_content_count.setText(f"원고: {total}개")
        if rows_to_delete:
            self._log(f"원고 {len(rows_to_delete)}개 삭제 → 총 {total}개")

    def _select_all_manuscripts(self):
        """전체 선택/해제 토글."""
        if len(self._selected_ms_rows) == self.manuscript_table.rowCount() and self.manuscript_table.rowCount() > 0:
            # 전체 해제
            self._selected_ms_rows.clear()
            for r in range(self.manuscript_table.rowCount()):
                color = QColor("#ffffff") if r % 2 == 0 else QColor("#f8f8fc")
                for col in range(self.manuscript_table.columnCount()):
                    cell = self.manuscript_table.item(r, col)
                    if cell:
                        cell.setBackground(color)
        else:
            # 전체 선택
            for r in range(self.manuscript_table.rowCount()):
                self._selected_ms_rows.add(r)
                for col in range(self.manuscript_table.columnCount()):
                    cell = self.manuscript_table.item(r, col)
                    if cell:
                        cell.setBackground(QColor("#f4cccc"))

    def _on_manuscript_row_clicked(self, row, col):
        """행 클릭 시 선택/해제 토글."""
        if row in self._selected_ms_rows:
            self._selected_ms_rows.discard(row)
            color = QColor("#ffffff") if row % 2 == 0 else QColor("#f8f8fc")
        else:
            self._selected_ms_rows.add(row)
            color = QColor("#f4cccc")
        for c in range(self.manuscript_table.columnCount()):
            cell = self.manuscript_table.item(row, c)
            if cell:
                cell.setBackground(color)

    def _log(self, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_area.appendPlainText(f"[{ts}] {msg}")

    def _on_start(self):
        # 구글시트에서 계정 로드
        self._log("구글시트에서 계정 로드 중...")
        try:
            accounts = func.load_accounts_from_gsheet()
        except Exception as e:
            self._log(f"구글시트 로드 실패: {str(e)}")
            QMessageBox.warning(self, "구글시트 오류", f"구글시트에서 계정을 불러올 수 없습니다.\n\n원인: {str(e)}")
            return
        # accounts = [a for a in accounts if a["id"] == "magazine10885"]  # 테스트용 필터
        if not accounts:
            QMessageBox.warning(self, "알림", "구글시트에 계정 데이터가 없습니다. (A2행부터 입력)")
            return

        # 프록시 로드 (config.ini에서)
        cfg = func.load_config()
        proxy_path = cfg.get("paths", "proxy_file", fallback="")
        if not proxy_path or not os.path.isfile(proxy_path):
            QMessageBox.warning(self, "알림", "설정 탭에서 프록시 파일을 설정해주세요.")
            return
        proxies = func.load_proxies(proxy_path)
        if not proxies:
            QMessageBox.warning(self, "알림", "프록시 파일이 비어있습니다.")
            return

        self.btn_start.setEnabled(False)
        self.btn_pause.setEnabled(True)
        self.btn_stop.setEnabled(True)

        wc = self.worker_slider.value()

        # 아이디별 그룹핑
        groups = func.group_accounts_by_id(accounts)

        # 프록시 셔플
        import random
        random.shuffle(proxies)

        self._log(f"작업 시작 — 계정 {len(accounts)}행 → {len(groups)}개 그룹 / 프록시 {len(proxies)}개")

        # 원고 로드 (테이블에 있는 원고 경로 기반)
        manuscripts = []
        for r in range(self.manuscript_table.rowCount()):
            path_item = self.manuscript_table.item(r, 3)
            if path_item:
                ms = func._parse_manuscript_folder(path_item.text())
                if ms:
                    manuscripts.append(ms)
        if not manuscripts:
            QMessageBox.warning(self, "알림", "원고 폴더를 선택하고 소폴더(키워드)가 있는지 확인해주세요.")
            self.btn_start.setEnabled(True)
            self.btn_pause.setEnabled(False)
            self.btn_stop.setEnabled(False)
            return
        self._log(f"원고 {len(manuscripts)}개 로드 완료 (테이블 순서)")

        # 원고를 아이디별 작성수에 맞게 순차 배정
        ms_idx = 0
        ms_assignments = {}
        total_needed = sum(sum(t.get("post_count", 1) for t in grp.get("tasks", [])) for grp in groups)
        if total_needed > len(manuscripts):
            self._log(f"⚠ 원고 부족: 필요 {total_needed}개 / 보유 {len(manuscripts)}개 — 원고 수만큼만 작업합니다")
        for grp in groups:
            nid = grp["id"]
            total_posts = sum(t.get("post_count", 1) for t in grp.get("tasks", []))
            assigned = []
            for _ in range(total_posts):
                if ms_idx < len(manuscripts):
                    assigned.append(manuscripts[ms_idx])
                    ms_idx += 1
            ms_assignments[nid] = assigned
            if assigned:
                self._log(f"원고 배정: {nid} → {[m['name'] for m in assigned]}")

        # 원고 없는 계정 제외 → 워커 재분배
        active_groups = [grp for grp in groups if ms_assignments.get(grp["id"])]
        skipped = len(groups) - len(active_groups)
        if skipped > 0:
            self._log(f"⚠ 원고 없는 계정 {skipped}개 제외 → 활성 계정 {len(active_groups)}개")

        if not active_groups:
            QMessageBox.warning(self, "알림", "원고가 부족하여 작업할 계정이 없습니다.")
            self.btn_start.setEnabled(True)
            self.btn_pause.setEnabled(False)
            self.btn_stop.setEnabled(False)
            return

        # 워커 재분배 (활성 계정만)
        num_workers = min(wc, len(active_groups))
        worker_groups = [[] for _ in range(num_workers)]
        for i, grp in enumerate(active_groups):
            worker_groups[i % num_workers].append(grp)

        proxy_idx = 0
        worker_assignments = []
        for w_idx in range(num_workers):
            accs = worker_groups[w_idx]
            w_proxies = []
            for _ in range(len(accs)):
                w_proxies.append(proxies[proxy_idx % len(proxies)])
                proxy_idx += 1
            worker_assignments.append({
                "worker_idx": w_idx,
                "accounts": accs,
                "proxies": w_proxies,
            })

        # 워커 테이블 재표시
        self.worker_table.setRowCount(num_workers)
        for w in worker_assignments:
            w_idx = w["worker_idx"]
            acc_ids = [a["id"] for a in w["accounts"]]
            self.worker_table.setItem(w_idx, 0, QTableWidgetItem(str(w_idx + 1)))
            self.worker_table.setItem(w_idx, 1, QTableWidgetItem(f"{acc_ids[0]} +{len(acc_ids)-1}" if len(acc_ids) > 1 else acc_ids[0]))
            self.worker_table.setItem(w_idx, 2, QTableWidgetItem(w["proxies"][0][:20] if w["proxies"] else "-"))
            self.worker_table.setItem(w_idx, 3, QTableWidgetItem(f"{len(acc_ids)}개 계정"))
            self.worker_table.setItem(w_idx, 4, QTableWidgetItem(""))
            item = QTableWidgetItem("대기중")
            item.setForeground(QColor("#b08800"))
            self.worker_table.setItem(w_idx, 5, item)

        self._log(f"워커 재분배: {len(active_groups)}개 계정 → {num_workers}개 워커")
        for w in worker_assignments:
            acc_ids = [a["id"] for a in w["accounts"]]
            self._log(f"워커#{w['worker_idx']+1} 배정: {acc_ids}")

        # 설정 수집
        settings = {
            "write_mode": self.write_mode.currentText(),
            "page_lo": self.page_lo.value(),
            "page_hi": self.page_hi.value(),
            "delay_lo": self.delay_lo.value(),
            "delay_hi": self.delay_hi.value(),
            "grade_filter": [i - 1 for i, (n, cb) in enumerate(self.grade_checks.items()) if cb.isChecked()],
            "auto_join": self.chk_auto_join.isChecked(),
            "delete_images": self.chk_delete_images.isChecked(),
            "post_options": {
                "allow_comment": self.chk_allow_comment.isChecked(),
                "allow_search": self.chk_allow_search.isChecked(),
                "public": self.chk_public.isChecked(),
            },
            "manuscripts": manuscripts,
            "ms_assignments": ms_assignments,
            "contents": [],
        }

        # 워커 스레드 시작
        self._worker_thread = LoginWorkerThread(worker_assignments, proxies, settings)
        self._worker_thread.log_signal.connect(self._log)
        self._worker_thread.worker_update.connect(self._update_worker_table)
        self._worker_thread.finished_signal.connect(self._on_finished)
        self._worker_thread.start()

    def _update_worker_table(self, idx, status):
        item = QTableWidgetItem(status)
        if "성공" in status or "완료" in status:
            item.setForeground(QColor("#2e7d32"))
        elif "실패" in status or "에러" in status or "해제 불가" in status or "영구정지" in status:
            item.setForeground(QColor("#c62828"))
        else:
            item.setForeground(QColor("#b08800"))
        self.worker_table.setItem(idx, 5, item)
        self._update_summary(self._worker_thread.results)

    def _on_finished(self, results):
        self._update_summary(results)
        self._log(f"=== {self.lbl_summary.text()} ===")
        self._log(f"=== {self.lbl_work_summary.text()} ===")

        # 미사용 원고 별도 폴더에 복사
        self._save_unused_manuscripts()

        self.btn_start.setEnabled(True)
        self.btn_pause.setEnabled(False)
        self.btn_stop.setEnabled(False)

    def _save_unused_manuscripts(self):
        """사용되지 않은 원고를 '미사용원고' 폴더에 복사."""
        import shutil
        if not hasattr(self, '_worker_thread'):
            return
        used = self._worker_thread.used_manuscripts
        all_manuscripts = []
        for r in range(self.manuscript_table.rowCount()):
            name_item = self.manuscript_table.item(r, 0)
            path_item = self.manuscript_table.item(r, 3)
            if name_item and path_item:
                all_manuscripts.append({"name": name_item.text(), "path": path_item.text()})

        unused = [m for m in all_manuscripts if m["name"] not in used]
        if not unused:
            self._log("미사용 원고 없음")
            return

        # 미사용원고 폴더 생성
        from datetime import datetime
        save_dir = os.path.join(func._get_base_dir(), f"미사용원고_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        os.makedirs(save_dir, exist_ok=True)

        for m in unused:
            src = m["path"]
            dst = os.path.join(save_dir, m["name"])
            try:
                shutil.copytree(src, dst)
            except Exception as e:
                self._log(f"미사용 원고 복사 실패: {m['name']} — {str(e)[:30]}")

        self._log(f"미사용 원고 {len(unused)}개 → {save_dir}")

    def _update_summary(self, results):
        ok = len([r for r in results if r["ok"]])
        bday = len([r for r in results if r.get("error") == "blocked_birthday"])
        phone = len([r for r in results if r.get("error") == "blocked_phone"])
        perm = len([r for r in results if r.get("error") == "permanent_ban"])
        captcha = len([r for r in results if r.get("error") == "captcha"])
        security = len([r for r in results if r.get("error") == "security"])
        fail = len([r for r in results if not r["ok"] and r.get("error") not in
                    ("blocked_birthday", "blocked_phone", "permanent_ban", "captcha", "security")])
        total = len(results)
        self.lbl_summary.setText(
            f"로그인: 성공 {ok} | 생년월일 {bday} | 핸드폰 {phone} | 영구정지 {perm} | 캡차 {captcha} | 보안인증 {security} | 실패 {fail} / 총 {total}개"
        )
        # 작업 결과
        if hasattr(self, '_worker_thread'):
            ws = self._worker_thread.work_stats
            self.lbl_work_summary.setText(
                f"작업: 답글성공 {ws['reply_ok']} | 답글실패 {ws['reply_fail']} | 글쓰기성공 {ws['write_ok']} | 글쓰기실패 {ws['write_fail']} | 활동정지 {ws['suspended']} | 미가입 {ws['not_member']}"
            )

    def _on_stop(self):
        if hasattr(self, '_worker_thread') and self._worker_thread.isRunning():
            self._worker_thread.stop()
            self._log("중지 요청됨... 워커 종료 후 크롬 드라이버를 닫습니다.")
        self.btn_start.setEnabled(True)
        self.btn_pause.setEnabled(False)
        self.btn_pause.setText("⏸  일시정지")
        self.btn_stop.setEnabled(False)

    def _on_pause(self):
        if not hasattr(self, '_worker_thread') or not self._worker_thread.isRunning():
            return
        if self._worker_thread._pause_flag:
            # 재개
            self._worker_thread.resume()
            self.btn_pause.setText("⏸  일시정지")
            self._log("▶ 작업 재개")
        else:
            # 일시정지
            self._worker_thread.pause()
            self.btn_pause.setText("▶  재개")
            self._log("⏸ 일시정지됨 — 현재 작업 완료 후 대기")


# ─────────────────────────────────────────────
# 2~6순위: 미정 탭
# ─────────────────────────────────────────────
class PlaceholderTab(QWidget):
    def __init__(self, name, features, cost, days):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(16)

        badge = QLabel("개발 예정")
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setFixedHeight(32)
        badge.setStyleSheet(
            "background-color: #fff3cd; color: #856404; border: 1px solid #ffc107; "
            "border-radius: 4px; font-size: 13px; font-weight: bold; padding: 0 20px;"
        )
        badge.setFixedWidth(120)
        bl = QHBoxLayout()
        bl.addStretch(); bl.addWidget(badge); bl.addStretch()
        layout.addLayout(bl)

        title = QLabel(name)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(QFont("", 18, QFont.Weight.Bold))
        title.setStyleSheet("color: #202030;")
        layout.addWidget(title)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("background-color: #d0d0d8; max-height: 1px;")
        layout.addWidget(sep)

        fg = QGroupBox("주요 기능 (예정)")
        fl = QVBoxLayout(fg)
        for i, feat in enumerate(features, 1):
            lbl = QLabel(f"  {i}. {feat}")
            lbl.setStyleSheet("color: #404050; font-size: 13px; padding: 3px 0;")
            fl.addWidget(lbl)
        layout.addWidget(fg)

        info = QHBoxLayout()
        for label, value, color in [("개발 비용", cost, "#1565c0"), ("예상 작업기간", days, "#2e7d32")]:
            g = QGroupBox(label)
            gl = QVBoxLayout(g)
            v = QLabel(value)
            v.setFont(QFont("", 14, QFont.Weight.Bold))
            v.setStyleSheet(f"color: {color};")
            v.setAlignment(Qt.AlignmentFlag.AlignCenter)
            gl.addWidget(v)
            info.addWidget(g)
        layout.addLayout(info)

        notice = QLabel(
            "이 탭은 기획 확정 후 UI가 구현될 예정입니다.\n"
            "1순위 카페 글쓰기 프로그램 개발 완료 후 순차적으로 착수합니다."
        )
        notice.setAlignment(Qt.AlignmentFlag.AlignCenter)
        notice.setStyleSheet("color: #909098; font-size: 12px; padding: 20px;")
        layout.addWidget(notice)
        layout.addStretch()


# ─────────────────────────────────────────────
# 4순위: 카페 육성 탭
# ─────────────────────────────────────────────
class CafeNurturingTab(QWidget):
    def __init__(self):
        super().__init__()
        self._init_ui()

    def _init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # ══════════════════════════════════
        # 좌측: 설정 패널
        # ══════════════════════════════════
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)

        # ── 워커 설정 ──
        worker_group = QGroupBox("워커 설정")
        wkg = QGridLayout(worker_group)
        wkg.addWidget(QLabel("워커 수:"), 0, 0)
        self.worker_slider = LabeledSlider(1, 50, 50)
        wkg.addWidget(self.worker_slider, 0, 1, 1, 2)
        left_layout.addWidget(worker_group)

        # ── 육성 대상 카페 ──
        cafe_group = QGroupBox("육성 대상 카페")
        cg = QVBoxLayout(cafe_group)
        cg.addWidget(QLabel("구글시트에서 카페 URL을 로드합니다."))
        self.cafe_table = QTableWidget(0, 4)
        self.cafe_table.setHorizontalHeaderLabels(["카페 URL", "현재 등급", "목표 등급", "상태"])
        ch = self.cafe_table.horizontalHeader()
        ch.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        ch.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        ch.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        ch.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.cafe_table.setColumnWidth(1, 80)
        self.cafe_table.setColumnWidth(2, 80)
        self.cafe_table.setColumnWidth(3, 80)
        self.cafe_table.setMaximumHeight(200)
        self.cafe_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.cafe_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.cafe_table.setAlternatingRowColors(True)
        cg.addWidget(self.cafe_table)
        left_layout.addWidget(cafe_group)

        # ── 육성 설정 ──
        nurture_group = QGroupBox("육성 설정")
        ng = QGridLayout(nurture_group)

        ng.addWidget(QLabel("목표 등급:"), 0, 0)
        self.target_grade = QComboBox()
        self.target_grade.addItems(["1단계 (자동)", "2단계", "3단계"])
        ng.addWidget(self.target_grade, 0, 1)

        ng.addWidget(QLabel("활동 유형:"), 1, 0)
        self.chk_checkin = QCheckBox("출석")
        self.chk_checkin.setChecked(True)
        ng.addWidget(self.chk_checkin, 1, 1)
        self.chk_comment = QCheckBox("댓글")
        self.chk_comment.setChecked(True)
        ng.addWidget(self.chk_comment, 1, 2)
        self.chk_write = QCheckBox("글쓰기")
        self.chk_write.setChecked(True)
        ng.addWidget(self.chk_write, 2, 1)
        self.chk_like = QCheckBox("좋아요")
        self.chk_like.setChecked(True)
        ng.addWidget(self.chk_like, 2, 2)

        ng.addWidget(QLabel("딜레이(초):"), 3, 0)
        delay_layout = QHBoxLayout()
        self.delay_lo = QSpinBox()
        self.delay_lo.setRange(1, 600)
        self.delay_lo.setValue(3)
        delay_layout.addWidget(self.delay_lo)
        delay_layout.addWidget(QLabel("~"))
        self.delay_hi = QSpinBox()
        self.delay_hi.setRange(1, 600)
        self.delay_hi.setValue(8)
        delay_layout.addWidget(self.delay_hi)
        delay_layout.addWidget(QLabel("초"))
        ng.addLayout(delay_layout, 3, 1, 1, 2)

        left_layout.addWidget(nurture_group)

        # ── 원고 관리 ──
        content_group = QGroupBox("원고 관리 (글쓰기/답글용)")
        ccg = QVBoxLayout(content_group)
        folder_row = QHBoxLayout()
        folder_row.addWidget(QLabel("원고 대폴더:"))
        self.content_folder = QLineEdit()
        self.content_folder.setPlaceholderText("대폴더 경로")
        folder_row.addWidget(self.content_folder)
        btn_folder = QPushButton("폴더 선택")
        btn_folder.setProperty("class", "secondary")
        btn_folder.setFixedWidth(80)
        btn_folder.clicked.connect(self._browse_folder)
        folder_row.addWidget(btn_folder)
        self.lbl_content_count = QLabel("원고: 0개")
        self.lbl_content_count.setStyleSheet("color: #606070; font-weight: bold;")
        folder_row.addWidget(self.lbl_content_count)
        ccg.addLayout(folder_row)
        left_layout.addWidget(content_group)

        left_layout.addStretch()

        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setWidget(left_panel)
        left_scroll.setFrameShape(QFrame.Shape.NoFrame)
        left_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        left_scroll.setMinimumWidth(420)

        # ══════════════════════════════════
        # 우측: 실행 / 모니터링 패널
        # ══════════════════════════════════
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(8)

        # ── 실행 컨트롤 ──
        ctrl_group = QGroupBox("실행 제어")
        ctrl_layout = QHBoxLayout(ctrl_group)

        self.btn_start = QPushButton("▶  육성 시작")
        self.btn_start.setProperty("class", "success")
        self.btn_start.setMinimumHeight(38)
        ctrl_layout.addWidget(self.btn_start)

        self.btn_pause = QPushButton("⏸  일시정지")
        self.btn_pause.setEnabled(False)
        self.btn_pause.setMinimumHeight(38)
        ctrl_layout.addWidget(self.btn_pause)

        self.btn_stop = QPushButton("⏹  중지")
        self.btn_stop.setProperty("class", "danger")
        self.btn_stop.setEnabled(False)
        self.btn_stop.setMinimumHeight(38)
        ctrl_layout.addWidget(self.btn_stop)

        right_layout.addWidget(ctrl_group)

        # ── 육성 진행 대시보드 ──
        dash_group = QGroupBox("육성 진행 대시보드")
        dash_layout = QVBoxLayout(dash_group)

        self.dash_table = QTableWidget(0, 8)
        self.dash_table.setHorizontalHeaderLabels([
            "워커#", "계정", "카페", "현재등급", "목표등급", "출석", "댓글/글", "상태"
        ])
        dh = self.dash_table.horizontalHeader()
        dh.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        dh.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.dash_table.setColumnWidth(0, 50)
        self.dash_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.dash_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.dash_table.setAlternatingRowColors(True)
        dash_layout.addWidget(self.dash_table)

        # 요약
        self.lbl_summary = QLabel("로그인: 0 | 가입: 0 | 육성중: 0 | 등업완료: 0 | 실패: 0")
        self.lbl_summary.setFont(QFont("Malgun Gothic", 11, QFont.Weight.Bold))
        self.lbl_summary.setStyleSheet("color: #303050;")
        dash_layout.addWidget(self.lbl_summary)

        right_layout.addWidget(dash_group)

        # ── 로그 ──
        log_group = QGroupBox("결과 로그")
        log_layout = QVBoxLayout(log_group)

        self.log_area = QPlainTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setMaximumBlockCount(1000)
        self.log_area.setFont(QFont("Malgun Gothic", 10))
        self.log_area.setStyleSheet("background-color: #fafafa; color: #202030; border: 1px solid #c0c0cc;")
        log_layout.addWidget(self.log_area)

        log_btn_layout = QHBoxLayout()
        btn_clear = QPushButton("로그 지우기")
        btn_clear.setProperty("class", "secondary")
        btn_clear.clicked.connect(self.log_area.clear)
        log_btn_layout.addWidget(btn_clear)
        log_btn_layout.addStretch()
        log_layout.addLayout(log_btn_layout)

        right_layout.addWidget(log_group)

        # 스플리터 조립
        splitter.addWidget(left_scroll)
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 6)

        main_layout.addWidget(splitter)

        self._log("카페 육성 프로그램 초기화 완료")
        self._log("기능 개발 진행 중 — 설정 UI만 활성화 상태입니다.")

    def _log(self, msg):
        from datetime import datetime
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_area.appendPlainText(f"[{ts}] {msg}")

    def _browse_folder(self):
        path = QFileDialog.getExistingDirectory(self, "원고 대폴더 선택")
        if path:
            self.content_folder.setText(path)
            items = func.get_manuscript_display_list(path)
            self.lbl_content_count.setText(f"원고: {len(items)}개")
            self._log(f"원고 폴더 로드: {len(items)}개 키워드")


# ─────────────────────────────────────────────
# 메인 윈도우
# ─────────────────────────────────────────────
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("네이버 카페 자동화 프로그램 (6종)  |  SOFTCAT")
        self.setMinimumSize(1200, 700)
        self.resize(1400, 900)

        # 윈도우 아이콘 설정
        from PyQt6.QtGui import QIcon
        icon_path = os.path.join(func._get_base_dir(), "softcat2.ico")
        if os.path.isfile(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        central = QWidget()
        self.setCentralWidget(central)
        ml = QVBoxLayout(central)
        ml.setContentsMargins(6, 6, 6, 6)

        # 헤더
        header = QHBoxLayout()
        logo = QLabel("🐱 SOFTCAT")
        logo.setFont(QFont("", 14, QFont.Weight.Bold))
        logo.setStyleSheet("color: #4a6cf7;")
        header.addWidget(logo)
        title = QLabel("네이버 카페 자동화")
        title.setFont(QFont("", 14))
        title.setStyleSheet("color: #808090;")
        header.addWidget(title)
        header.addStretch()
        ver = QLabel("v1.0.0  |  SC-2026-0401-CF")
        ver.setStyleSheet("color: #a0a0a8; font-size: 11px;")
        header.addWidget(ver)
        ml.addLayout(header)

        # 탭
        tabs = QTabWidget()
        tabs.setDocumentMode(True)

        tabs.addTab(CafeWriterTab(), "1. 카페 글쓰기")
        tabs.addTab(PlaceholderTab(
            "계정별 카페 상태체크 프로그램 (워커)",
            ["다수 계정 일괄 로그인 및 상태 조회", "활동정지 / 영구정지 / 보조조치 상태 확인",
             "카페별 아이디 등급 조회", "멀티워커 병렬 처리", "결과 구글시트 자동 기록"],
            "1,200,000원", "7 영업일"), "2. 상태체크")
        tabs.addTab(PlaceholderTab(
            "댓글 프로그램 (워커)",
            ["대상 게시글 자동 탐색 및 댓글 작성", "댓글 내용 템플릿 / Gemini 자동 생성",
             "계정별 댓글 간격 / 빈도 조절", "멀티워커 병렬 처리 (프록시 연동)", "결과 로깅 및 구글시트 기록"],
            "1,500,000원", "9 영업일"), "3. 댓글")
        tabs.addTab(CafeNurturingTab(), "4. 카페 육성")
        tabs.addTab(PlaceholderTab(
            "카페별 등급파악 프로그램",
            ["카페별 등급 체계 자동 크롤링", "등업 조건 (글 수, 댓글 수, 출석 등) 파싱",
             "등급별 권한 (글쓰기, 댓글 등) 정리", "결과 구글시트 / DB 자동 기록"],
            "1,000,000원", "5 영업일"), "5. 등급파악")
        tabs.addTab(PlaceholderTab(
            "카페 가입 프로그램 (워커)",
            ["카페 가입 양식 자동 인식 및 입력", "가입 질문 Gemini 자동 응답",
             "다수 계정 일괄 가입 처리", "멀티워커 병렬 처리 (프록시 연동)", "가입 결과 구글시트 기록"],
            "1,000,000원", "7 영업일"), "6. 카페 가입")
        tabs.addTab(SettingsTab(), "⚙ 설정")

        ml.addWidget(tabs)
        self.statusBar().showMessage("준비됨  |  SOFTCAT © 2026  |  HOON COMPANY 귀하")


# ─────────────────────────────────────────────
# API 키 인증 창
# ─────────────────────────────────────────────
class ApiKeyAuthWindow(QDialog):
    PRODUCT_ID = 12
    ADMIN_KEY = "softcat-admin-2026"
    API_HOST = "http://13.209.199.124:8080"

    def __init__(self):
        super().__init__()
        self.setWindowTitle("SOFTCAT 인증")
        self.setFixedSize(420, 280)
        self.authenticated = False
        self.user_info = {}

        # 아이콘
        from PyQt6.QtGui import QIcon
        icon_path = os.path.join(func._get_base_dir(), "softcat2.ico")
        if os.path.isfile(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(12)

        title = QLabel("SOFTCAT 네이버 카페 자동화")
        title.setFont(QFont("Malgun Gothic", 16, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("color: #4a6cf7;")
        layout.addWidget(title)

        subtitle = QLabel("API 키를 입력하여 인증해주세요.")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("color: #606070; font-size: 12px;")
        layout.addWidget(subtitle)

        layout.addSpacing(10)

        self.api_key_input = QLineEdit()
        self.api_key_input.setPlaceholderText("API 키 입력")
        self.api_key_input.setMinimumHeight(36)
        self.api_key_input.setStyleSheet("font-size: 13px; padding: 6px 10px; border: 1px solid #b0b0c0; border-radius: 4px;")
        self.api_key_input.returnPressed.connect(self._authenticate)
        layout.addWidget(self.api_key_input)

        self.btn_auth = QPushButton("인증")
        self.btn_auth.setMinimumHeight(38)
        self.btn_auth.setStyleSheet("background-color: #4a6cf7; color: white; font-size: 13px; font-weight: bold; border: none; border-radius: 4px;")
        self.btn_auth.clicked.connect(self._authenticate)
        layout.addWidget(self.btn_auth)

        self.lbl_error = QLabel("")
        self.lbl_error.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_error.setStyleSheet("color: #e53935; font-size: 11px;")
        self.lbl_error.setVisible(False)
        layout.addWidget(self.lbl_error)

        self.lbl_info = QLabel("SOFTCAT | HOON COMPANY")
        self.lbl_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_info.setStyleSheet("color: #a0a0a8; font-size: 10px;")
        layout.addWidget(self.lbl_info)

        layout.addStretch()

    def _get_mac_address(self):
        import psutil
        for name, addrs in psutil.net_if_addrs().items():
            stats = psutil.net_if_stats().get(name)
            if stats and stats.isup and name != 'lo':
                for addr in addrs:
                    if addr.family == psutil.AF_LINK and addr.address and addr.address != '00:00:00:00:00:00':
                        return addr.address.replace('-', ':').upper()
        import uuid
        mac = uuid.getnode()
        return ':'.join(f'{(mac >> (8 * i)) & 0xff:02x}' for i in reversed(range(6)))

    def _show_error(self, msg):
        self.lbl_error.setText(msg)
        self.lbl_error.setVisible(True)

    def _authenticate(self):
        import urllib.request
        import json

        api_key = self.api_key_input.text().strip()
        if not api_key:
            self._show_error("API 키를 입력해주세요.")
            return

        self.btn_auth.setEnabled(False)
        self.lbl_error.setVisible(False)

        try:
            # 관리자 키
            if api_key == self.ADMIN_KEY:
                self.user_info = {"nickname": "관리자", "api_key": api_key, "remaining_days": 9999}
                self.authenticated = True
                self.accept()
                return

            # 1. API 키 인증
            auth_url = f"{self.API_HOST}/api/subscription/hash-key-auth/temp?id={self.PRODUCT_ID}&hashKey={api_key}"
            req = urllib.request.Request(auth_url)
            with urllib.request.urlopen(req, timeout=10) as resp:
                auth_data = json.loads(resp.read().decode())

            # 2. MAC 주소 검증
            mac = self._get_mac_address()
            mac_url = f"{self.API_HOST}/api/subscription/verify-mac/temp?id={self.PRODUCT_ID}&hashKey={api_key}&macAddress={mac}"
            req2 = urllib.request.Request(mac_url, method="POST")
            with urllib.request.urlopen(req2, timeout=10) as resp2:
                mac_data = json.loads(resp2.read().decode())

            if mac_data.get("result") == "fail":
                self._show_error("MAC 주소 인증에 실패하였습니다.")
                return

            # 3. 사용자 정보
            nickname = auth_data.get("name", "사용자")
            remaining = auth_data.get("remainingDays", 0)
            self.user_info = {"nickname": nickname, "api_key": api_key, "remaining_days": remaining}
            self.authenticated = True
            self.accept()

        except urllib.error.HTTPError:
            self._show_error("API 인증에 실패하였습니다.")
        except Exception as e:
            self._show_error(f"연결 오류: {str(e)[:50]}")
        finally:
            self.btn_auth.setEnabled(True)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet(STYLE_SHEET)
    app.setFont(QFont("Malgun Gothic", 10))

    # 인증 창
    auth = ApiKeyAuthWindow()
    if auth.exec() != QDialog.DialogCode.Accepted or not auth.authenticated:
        sys.exit(0)

    # 인증 성공 → 메인 윈도우
    window = MainWindow()
    info = auth.user_info
    window.statusBar().showMessage(
        f"준비됨  |  {info.get('nickname', '')}님  |  잔여 {info.get('remaining_days', 0)}일  |  SOFTCAT © 2026  |  HOON COMPANY"
    )
    window.show()
    sys.exit(app.exec())
