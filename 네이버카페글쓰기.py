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
    QProgressBar, QAbstractItemView, QScrollArea
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QColor

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
        gsg.addWidget(QLabel("API 키:"), 0, 0)
        self.gs_api_key = QLineEdit()
        self.gs_api_key.setPlaceholderText("Google Sheets API 키")
        self.gs_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        gsg.addWidget(self.gs_api_key, 0, 1)
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
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.ini")

    def _load_config(self):
        cfg = configparser.ConfigParser()
        cfg.read(self._config_path(), encoding="utf-8")
        self.gs_api_key.setText(cfg.get("google_sheets", "api_key", fallback=""))
        self.gs_sheet_id.setText(cfg.get("google_sheets", "sheet_id", fallback=""))
        self.gemini_api_key.setText(cfg.get("gemini", "api_key", fallback=""))
        self.proxy_file_edit.setText(cfg.get("paths", "proxy_file", fallback=""))

    def _save_config(self):
        cfg = configparser.ConfigParser()
        cfg["gemini"] = {"api_key": self.gemini_api_key.text()}
        cfg["google_sheets"] = {"api_key": self.gs_api_key.text(), "sheet_id": self.gs_sheet_id.text()}
        cfg["paths"] = {"proxy_file": self.proxy_file_edit.text()}
        with open(self._config_path(), "w", encoding="utf-8") as f:
            cfg.write(f)
        QMessageBox.information(self, "저장 완료", "설정이 config.ini에 저장되었습니다.")

# ─────────────────────────────────────────────

# ─────────────────────────────────────────────
# 로그인 워커 스레드
# ─────────────────────────────────────────────
class LoginWorkerThread(QThread):
    """순차적으로 계정 로그인을 수행하는 워커 스레드."""
    log_signal = pyqtSignal(str)
    worker_update = pyqtSignal(int, str)  # idx, status
    finished_signal = pyqtSignal(list)  # results

    def __init__(self, accounts, proxies, worker_count, settings=None):
        super().__init__()
        self.accounts = accounts
        self.proxies = proxies
        self.worker_count = worker_count
        self.settings = settings or {}
        self.drivers = []
        self.results = []
        self._stop_flag = False

    def stop(self):
        self._stop_flag = True

    def run(self):
        import concurrent.futures
        count = min(self.worker_count, len(self.accounts), len(self.proxies))

        # ── 초기 정리 (임시 폴더만, 크롬 프로세스는 안 죽임) ──
        import shutil, tempfile, glob
        tmp = tempfile.gettempdir()
        for d in glob.glob(os.path.join(tmp, "uc_worker_*")):
            try:
                shutil.rmtree(d, ignore_errors=True)
            except:
                pass
        self.log_signal.emit("임시 폴더 정리 완료")

        # ── 1단계: 로그인 순차 실행 ──
        self.log_signal.emit("=== 1단계: 로그인 (순차) ===")
        for i in range(count):
            if self._stop_flag:
                break

            acc = self.accounts[i]
            proxy = self.proxies[i]
            nid = acc["id"]

            self.log_signal.emit(f"워커#{i+1} 프록시={proxy} / ID={nid}")
            self.worker_update.emit(i, "로그인 중...")

            try:
                driver = func.create_driver(proxy, i)
                log_fn = lambda msg, _i=i: self.log_signal.emit(f"  워커#{_i+1} {msg}")
                result = func.naver_login(driver, acc, log_fn)
                result["worker"] = i
                result["id"] = nid
                self.results.append(result)

                if result["ok"]:
                    self.worker_update.emit(i, "로그인 성공")
                    self.log_signal.emit(f"워커#{i+1} [성공] [{nid}] {result['msg']}")
                    self.drivers.append((i, acc, driver))
                else:
                    self.worker_update.emit(i, result["msg"][:30])
                    self.log_signal.emit(f"워커#{i+1} [실패] [{nid}] {result['msg']}")
                    if result.get("error") in ("blocked_phone", "permanent_ban", "login_fail", "exception"):
                        try:
                            driver.quit()
                        except:
                            pass
                    else:
                        self.drivers.append((i, acc, driver))

            except Exception as e:
                self.log_signal.emit(f"워커#{i+1} [실패] [{nid}] {str(e)[:60]}")
                self.worker_update.emit(i, f"에러: {str(e)[:20]}")

        # 로그인 결과 집계
        ok = len([r for r in self.results if r["ok"]])
        total = len(self.results)
        self.log_signal.emit(f"=== 로그인 완료: 성공 {ok}/{total} ===")

        # ── 2단계: 카페 작업 병렬 실행 ──
        logged_in = [(i, acc, drv) for i, acc, drv in self.drivers if any(
            r["ok"] and r["worker"] == i for r in self.results)]

        if logged_in and not self._stop_flag:
            import threading
            cafe_grades = {}  # {cafe_url: grade_info}
            cafe_grades_lock = threading.Lock()

            # ── 2단계: 카페 접속 + 등급 조회 + 작업 (병렬) ──
            self.log_signal.emit(f"=== 2단계: 카페 작업 (병렬 {len(logged_in)}개) ===")

            def cafe_task(worker_idx, grp, drv):
                log_fn = lambda msg: self.log_signal.emit(f"  워커#{worker_idx+1} {msg}")
                nid = grp["id"]
                tasks = grp.get("tasks", [])

                for t_idx, task in enumerate(tasks):
                    if self._stop_flag:
                        break

                    cafe_url = task.get("cafe_url", "")
                    if not cafe_url:
                        continue

                    cafe_short = cafe_url.replace("https://cafe.naver.com/", "")
                    self.worker_update.emit(worker_idx, f"카페 접속: {cafe_short} ({t_idx+1}/{len(tasks)})")
                    self.log_signal.emit(f"워커#{worker_idx+1} [{nid}] 카페 접속: {cafe_short}")

                    try:
                        acc_for_task = {**grp, **task}
                        cafe_result = func.visit_cafe(drv, acc_for_task, log_fn)

                        if cafe_result.get("ok"):
                            # 등급 조회 (캐시 — 같은 카페면 1번만)
                            with cafe_grades_lock:
                                if cafe_url not in cafe_grades:
                                    self.log_signal.emit(f"워커#{worker_idx+1} [{nid}] 등급 조회: {cafe_short}")
                                    grade_info = func.get_cafe_grades(drv, cafe_url, log_fn)
                                    cafe_grades[cafe_url] = grade_info

                            self.worker_update.emit(worker_idx, f"답글 작성: {cafe_short}")
                            work_result = func.do_cafe_work(drv, acc_for_task, cafe_grades, self.settings, log_fn)
                            self.log_signal.emit(f"워커#{worker_idx+1} [{nid}] {cafe_short}: {work_result['msg']}")
                        elif cafe_result.get("need_join") and self.settings.get("auto_join"):
                            self.log_signal.emit(f"워커#{worker_idx+1} [{nid}] {cafe_short}: 미가입 - 자동가입 ON (가입 로직 미구현)")
                            self.worker_update.emit(worker_idx, f"미가입: {cafe_short} (가입 미구현)")
                        else:
                            self.log_signal.emit(f"워커#{worker_idx+1} [{nid}] {cafe_short}: {cafe_result['msg']}")
                            self.worker_update.emit(worker_idx, f"미가입: {cafe_short}")
                    except Exception as ce:
                        self.log_signal.emit(f"워커#{worker_idx+1} [{nid}] {cafe_short} 에러: {str(ce)[:60]}")

                self.worker_update.emit(worker_idx, f"완료 ({len(tasks)}개 카페)")

            with concurrent.futures.ThreadPoolExecutor(max_workers=len(logged_in)) as pool:
                futures = [pool.submit(cafe_task, i, grp, drv) for i, grp, drv in logged_in]
                concurrent.futures.wait(futures)

            self.log_signal.emit("=== 카페 접속 완료 ===")

        self.finished_signal.emit(self.results)

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
        self.manuscript_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.manuscript_table.setAlternatingRowColors(True)
        cg.addWidget(self.manuscript_table)

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
        wg.addWidget(self.chk_allow_comment, 3, 0, 1, 3)

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
        summary_layout = QHBoxLayout()
        self.lbl_summary = QLabel("성공 0 | 생년월일 0 | 핸드폰 0 | 영구정지 0 | 캡차 0 | 보안인증 0 | 실패 0 / 총 0개")
        self.lbl_summary.setFont(QFont("Malgun Gothic", 11, QFont.Weight.Bold))
        self.lbl_summary.setStyleSheet("color: #303050;")
        summary_layout.addWidget(self.lbl_summary)
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
    def _browse_file(self, target, filt="모든 파일 (*.*)"):
        path, _ = QFileDialog.getOpenFileName(self, "파일 선택", "", filt)
        if path:
            target.setText(path)

    def _browse_folder(self):
        path = QFileDialog.getExistingDirectory(self, "원고 대폴더 선택")
        if path:
            self.content_folder.setText(path)
            # 소폴더 스캔 (랜덤 순서)
            items = func.get_manuscript_display_list(path)
            self.manuscript_table.setRowCount(len(items))
            for i, item in enumerate(items):
                self.manuscript_table.setItem(i, 0, QTableWidgetItem(item["name"]))
                self.manuscript_table.setItem(i, 1, QTableWidgetItem(str(item["txt_count"])))
                self.manuscript_table.setItem(i, 2, QTableWidgetItem(str(item["img_count"])))
                self.manuscript_table.setItem(i, 3, QTableWidgetItem(item["path"]))
            self.lbl_content_count.setText(f"원고: {len(items)}개")
            self._log(f"원고 폴더 로드: {len(items)}개 키워드 (랜덤 나열)")

    def _log(self, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_area.appendPlainText(f"[{ts}] {msg}")

    def _on_start(self):
        # 구글시트에서 계정 로드
        self._log("구글시트에서 계정 로드 중...")
        accounts = func.load_accounts_from_gsheet()
        if not accounts:
            QMessageBox.warning(self, "알림", "구글시트에서 계정을 불러올 수 없습니다.")
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
        count = min(wc, len(groups), len(proxies))

        # 프록시 셔플
        import random
        random.shuffle(proxies)

        self.worker_table.setRowCount(count)
        for i in range(count):
            grp = groups[i]
            proxy = proxies[i]
            # 첫 번째 작업의 카페 표시 (여러 개면 +N)
            cafes = [t["cafe_url"].replace("https://cafe.naver.com/", "") for t in grp["tasks"] if t["cafe_url"]]
            cafe_display = cafes[0] if cafes else "-"
            if len(cafes) > 1:
                cafe_display += f" +{len(cafes)-1}"
            task_count = sum(t["post_count"] for t in grp["tasks"])

            self.worker_table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
            self.worker_table.setItem(i, 1, QTableWidgetItem(grp["id"]))
            self.worker_table.setItem(i, 2, QTableWidgetItem(proxy[:20]))
            self.worker_table.setItem(i, 3, QTableWidgetItem(cafe_display))
            self.worker_table.setItem(i, 4, QTableWidgetItem(f"{len(grp['tasks'])}개 작업"))
            item = QTableWidgetItem("대기중")
            item.setForeground(QColor("#b08800"))
            self.worker_table.setItem(i, 5, item)

        self.lbl_summary.setText(f"성공 0 | 생년월일 0 | 핸드폰 0 | 영구정지 0 | 캡차 0 | 보안인증 0 | 실패 0 / 총 {count}개")

        self._log(f"작업 시작 — 계정 {len(accounts)}행 → {len(groups)}개 워커 / 프록시 {len(proxies)}개")

        # 원고 로드
        ms_folder = self.content_folder.text().strip()
        manuscripts = func.load_manuscripts(ms_folder) if ms_folder else []
        if not manuscripts:
            QMessageBox.warning(self, "알림", "원고 폴더를 선택하고 소폴더(키워드)가 있는지 확인해주세요.")
            self.btn_start.setEnabled(True)
            self.btn_pause.setEnabled(False)
            self.btn_stop.setEnabled(False)
            return
        self._log(f"원고 {len(manuscripts)}개 로드 완료 (랜덤 셔플)")

        # 설정 수집
        settings = {
            "page_lo": self.page_lo.value(),
            "page_hi": self.page_hi.value(),
            "delay_lo": self.delay_lo.value(),
            "delay_hi": self.delay_hi.value(),
            "grade_filter": [i for i, (n, cb) in enumerate(self.grade_checks.items()) if cb.isChecked()],
            "auto_join": self.chk_auto_join.isChecked(),
            "manuscripts": manuscripts,
            "contents": [],
        }

        # 워커 스레드 시작
        self._worker_thread = LoginWorkerThread(groups, proxies, count, settings)
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
        total = len(results)
        ok = len([r for r in results if r["ok"]])
        self._log(f"=== 결과: {self.lbl_summary.text()} ===")
        self.btn_start.setEnabled(True)
        self.btn_pause.setEnabled(False)
        self.btn_stop.setEnabled(False)

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
            f"성공 {ok} | 생년월일 {bday} | 핸드폰 {phone} | 영구정지 {perm} | 캡차 {captcha} | 보안인증 {security} | 실패 {fail} / 총 {total}개"
        )

    def _on_stop(self):
        if hasattr(self, '_worker_thread') and self._worker_thread.isRunning():
            self._worker_thread.stop()
            self._log("중지 요청됨... 현재 워커 완료 후 중지됩니다.")
        self.btn_start.setEnabled(True)
        self.btn_pause.setEnabled(False)
        self.btn_stop.setEnabled(False)


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
# 메인 윈도우
# ─────────────────────────────────────────────
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("네이버 카페 자동화 프로그램 (6종)  |  SOFTCAT")
        self.setMinimumSize(1200, 700)
        self.resize(1400, 900)

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
        tabs.addTab(PlaceholderTab(
            "카페 육성 프로그램",
            ["1순위 글쓰기 프로그램 기능 포함", "카페 가입 → 등업 조건 자동 파악",
             "1단계 등업까지 자동 활동 (출석, 댓글, 글쓰기 등)", "등급별 필요 활동량 자동 계산",
             "육성 진행 상태 대시보드"],
            "2,500,000원", "15 영업일"), "4. 카페 육성")
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


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet(STYLE_SHEET)
    app.setFont(QFont("Malgun Gothic", 10))
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
