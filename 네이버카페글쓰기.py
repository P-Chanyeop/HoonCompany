"""
네이버 카페 자동화 프로그램 (6종)
- 1순위: 카페 글쓰기 프로그램 (상세 GUI)
- 2~6순위: 탭/구조만 (미정)

SOFTCAT | SC-2026-0401-CF
"""

import sys
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
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor


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

        # ── 계정 / 프록시 설정 ──
        account_group = QGroupBox("계정 / 프록시 설정")
        ag = QGridLayout(account_group)

        ag.addWidget(QLabel("계정 파일:"), 0, 0)
        self.account_file_edit = QLineEdit()
        self.account_file_edit.setPlaceholderText("accounts.txt (ID:PW 형식)")
        ag.addWidget(self.account_file_edit, 0, 1)
        btn_acc = QPushButton("찾기")
        btn_acc.setProperty("class", "secondary")
        btn_acc.setFixedWidth(60)
        btn_acc.clicked.connect(lambda: self._browse_file(self.account_file_edit))
        ag.addWidget(btn_acc, 0, 2)

        ag.addWidget(QLabel("프록시:"), 1, 0)
        self.proxy_edit = QLineEdit()
        self.proxy_edit.setPlaceholderText("IP:PORT:USER:PW 또는 파일 경로")
        ag.addWidget(self.proxy_edit, 1, 1)
        proxy_btn_layout = QHBoxLayout()
        btn_ptxt = QPushButton("TXT")
        btn_ptxt.setProperty("class", "secondary")
        btn_ptxt.setFixedWidth(40)
        btn_ptxt.clicked.connect(lambda: self._browse_file(self.proxy_edit, "텍스트 (*.txt)"))
        proxy_btn_layout.addWidget(btn_ptxt)
        btn_pclear = QPushButton("X")
        btn_pclear.setProperty("class", "danger")
        btn_pclear.setFixedWidth(28)
        btn_pclear.clicked.connect(self.proxy_edit.clear)
        proxy_btn_layout.addWidget(btn_pclear)
        ag.addLayout(proxy_btn_layout, 1, 2)

        ag.addWidget(QLabel("워커 수:"), 2, 0)
        self.worker_slider = LabeledSlider(1, 60, 50)
        ag.addWidget(self.worker_slider, 2, 1, 1, 2)

        left_layout.addWidget(account_group)

        # ── 구글시트 연동 ──
        gsheet_group = QGroupBox("구글시트 연동")
        gg = QGridLayout(gsheet_group)

        gg.addWidget(QLabel("시트 URL:"), 0, 0)
        self.gsheet_url = QLineEdit()
        self.gsheet_url.setPlaceholderText("https://docs.google.com/spreadsheets/d/...")
        gg.addWidget(self.gsheet_url, 0, 1, 1, 2)

        gg.addWidget(QLabel("인증키 파일:"), 1, 0)
        self.gsheet_cred = QLineEdit()
        self.gsheet_cred.setPlaceholderText("credentials.json")
        gg.addWidget(self.gsheet_cred, 1, 1)
        btn_cred = QPushButton("찾기")
        btn_cred.setProperty("class", "secondary")
        btn_cred.setFixedWidth(60)
        btn_cred.clicked.connect(lambda: self._browse_file(self.gsheet_cred))
        gg.addWidget(btn_cred, 1, 2)

        gg.addWidget(QLabel("키워드 시트:"), 2, 0)
        self.keyword_sheet = QLineEdit("키워드")
        gg.addWidget(self.keyword_sheet, 2, 1)
        btn_sync = QPushButton("시트 동기화")
        btn_sync.setProperty("class", "secondary")
        gg.addWidget(btn_sync, 2, 2)

        gg.addWidget(QLabel("원고 시트:"), 3, 0)
        self.content_sheet = QLineEdit("원고")
        gg.addWidget(self.content_sheet, 3, 1)

        left_layout.addWidget(gsheet_group)

        # ── 원고 폴더 ──
        content_group = QGroupBox("원고 관리")
        cg = QGridLayout(content_group)

        cg.addWidget(QLabel("원고 폴더:"), 0, 0)
        self.content_folder = QLineEdit()
        self.content_folder.setPlaceholderText("원고 파일이 있는 폴더")
        cg.addWidget(self.content_folder, 0, 1)
        btn_folder = QPushButton("폴더 선택")
        btn_folder.setProperty("class", "secondary")
        btn_folder.setFixedWidth(70)
        btn_folder.clicked.connect(self._browse_folder)
        cg.addWidget(btn_folder, 0, 2)
        self.lbl_content_count = QLabel("원고: 0개")
        self.lbl_content_count.setStyleSheet("color: #606070;")
        cg.addWidget(self.lbl_content_count, 0, 3)

        left_layout.addWidget(content_group)

        # ── 글쓰기 설정 ──
        write_group = QGroupBox("글쓰기 설정")
        wg = QGridLayout(write_group)

        wg.addWidget(QLabel("카페 URL / ID:"), 0, 0)
        self.cafe_target = QLineEdit()
        self.cafe_target.setPlaceholderText("카페 URL 또는 카페 ID")
        wg.addWidget(self.cafe_target, 0, 1, 1, 2)

        wg.addWidget(QLabel("게시판 메뉴ID:"), 1, 0)
        self.menu_id_edit = QLineEdit()
        self.menu_id_edit.setPlaceholderText("비워두면 자동 탐색")
        wg.addWidget(self.menu_id_edit, 1, 1, 1, 2)

        wg.addWidget(QLabel("작성 모드:"), 2, 0)
        self.write_mode = QComboBox()
        self.write_mode.addItems(["글쓰기", "답글", "글쓰기 + 답글"])
        wg.addWidget(self.write_mode, 2, 1, 1, 2)

        wg.addWidget(QLabel("페이지 범위:"), 3, 0)
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
        wg.addLayout(page_range_layout, 3, 1, 1, 2)

        wg.addWidget(QLabel("딜레이(초):"), 4, 0)
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
        wg.addLayout(delay_range_layout, 4, 1, 1, 2)

        self.chk_allow_comment = QCheckBox("댓글허용")
        self.chk_allow_comment.setChecked(True)
        wg.addWidget(self.chk_allow_comment, 5, 0, 1, 3)

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

        # ── 보조조치 / API 설정 ──
        aux_group = QGroupBox("보조조치 해제 / API 설정")
        auxg = QGridLayout(aux_group)

        self.chk_auto_unblock = QCheckBox("보조조치 자동 해제")
        self.chk_auto_unblock.setChecked(True)
        auxg.addWidget(self.chk_auto_unblock, 0, 0, 1, 2)

        self.chk_auto_join = QCheckBox("카페 미가입 시 자동 가입")
        self.chk_auto_join.setChecked(True)
        auxg.addWidget(self.chk_auto_join, 1, 0, 1, 2)

        self.chk_grade_check = QCheckBox("등급 체크 후 글쓰기 (게시판 자동 탐색)")
        self.chk_grade_check.setChecked(True)
        auxg.addWidget(self.chk_grade_check, 2, 0, 1, 2)

        auxg.addWidget(QLabel("Gemini API Key:"), 3, 0)
        self.gemini_key = QLineEdit()
        self.gemini_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.gemini_key.setPlaceholderText("Gemini API 키")
        auxg.addWidget(self.gemini_key, 3, 1)

        auxg.addWidget(QLabel("Gemini 모델:"), 4, 0)
        self.gemini_model = QComboBox()
        self.gemini_model.addItems([
            "gemini-2.0-flash",
            "gemini-2.5-flash-preview",
            "gemini-2.5-pro-preview",
        ])
        auxg.addWidget(self.gemini_model, 4, 1)

        auxg.addWidget(QLabel("2Captcha API Key:"), 5, 0)
        self.captcha_key = QLineEdit()
        self.captcha_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.captcha_key.setPlaceholderText("2Captcha API 키")
        auxg.addWidget(self.captcha_key, 5, 1)

        left_layout.addWidget(aux_group)

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

        self.worker_table = QTableWidget(0, 7)
        self.worker_table.setHorizontalHeaderLabels([
            "워커#", "계정", "프록시", "상태", "카페", "게시판", "최근 작업"
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
        self.lbl_total = QLabel("전체: 0")
        self.lbl_running = QLabel("실행: 0")
        self.lbl_running.setStyleSheet("color: #2e7d32;")
        self.lbl_success = QLabel("성공: 0")
        self.lbl_success.setStyleSheet("color: #1565c0;")
        self.lbl_fail = QLabel("실패: 0")
        self.lbl_fail.setStyleSheet("color: #c62828;")
        for lbl in [self.lbl_total, self.lbl_running, self.lbl_success, self.lbl_fail]:
            lbl.setFont(QFont("", 11, QFont.Weight.Bold))
            summary_layout.addWidget(lbl)
        summary_layout.addStretch()
        worker_layout.addLayout(summary_layout)

        self.progress = QProgressBar()
        self.progress.setValue(0)
        self.progress.setFormat("%v / %m 완료 (%p%)")
        worker_layout.addWidget(self.progress)

        right_layout.addWidget(worker_group)

        # ── 로그 ──
        log_group = QGroupBox("결과 로그")
        log_layout = QVBoxLayout(log_group)

        self.log_area = QPlainTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setMaximumBlockCount(1000)
        self.log_area.setFont(QFont("Consolas", 10))
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
        path = QFileDialog.getExistingDirectory(self, "폴더 선택")
        if path:
            self.content_folder.setText(path)
            import os
            count = len([f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))])
            self.lbl_content_count.setText(f"원고: {count}개")

    def _log(self, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_area.appendPlainText(f"[{ts}] {msg}")

    def _on_start(self):
        if not self.account_file_edit.text().strip():
            QMessageBox.warning(self, "알림", "계정 파일을 선택해주세요.")
            return

        self.btn_start.setEnabled(False)
        self.btn_pause.setEnabled(True)
        self.btn_stop.setEnabled(True)

        wc = self.worker_slider.value()
        self.worker_table.setRowCount(wc)
        for i in range(wc):
            self.worker_table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
            self.worker_table.setItem(i, 1, QTableWidgetItem(f"account_{i+1}"))
            self.worker_table.setItem(i, 2, QTableWidgetItem(f"proxy_{i+1}"))
            item = QTableWidgetItem("대기중")
            item.setForeground(QColor("#b08800"))
            self.worker_table.setItem(i, 3, item)
            self.worker_table.setItem(i, 4, QTableWidgetItem("-"))
            self.worker_table.setItem(i, 5, QTableWidgetItem("-"))
            self.worker_table.setItem(i, 6, QTableWidgetItem("-"))

        self.lbl_total.setText(f"전체: {wc}")
        self.lbl_running.setText(f"실행: {wc}")
        self.progress.setMaximum(100)
        self.progress.setValue(0)

        mode = self.write_mode.currentText()
        checked = [n for n, cb in self.grade_checks.items() if cb.isChecked()]
        plo = self.page_lo.value()
        phi = self.page_hi.value()
        dlo = self.delay_lo.value()
        dhi = self.delay_hi.value()

        self._log(f"작업 시작 — 워커 {wc}개 / 모드: {mode}")
        self._log(f"페이지 {plo}~{phi} / 딜레이 {dlo}~{dhi}초")
        self._log(f"답글 등급: {', '.join(checked)}")
        self._log(f"댓글허용: {self.chk_allow_comment.isChecked()} / 보조조치 자동해제: {self.chk_auto_unblock.isChecked()}")

    def _on_stop(self):
        self.btn_start.setEnabled(True)
        self.btn_pause.setEnabled(False)
        self.btn_stop.setEnabled(False)
        self._log("작업 중지됨")


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

        ml.addWidget(tabs)
        self.statusBar().showMessage("준비됨  |  SOFTCAT © 2026  |  HOON COMPANY 귀하")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet(STYLE_SHEET)
    app.setFont(QFont("Malgun Gothic", 10))
    window = MainWindow()
    window.show()
    sys.exit(app.exec())