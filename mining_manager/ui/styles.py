THEME = """
/* ═══════════════════════════════════════════
   Mining Farm Manager — Dark Theme
   ═══════════════════════════════════════════ */

* {
    font-family: 'Segoe UI', 'SF Pro Display', Arial, sans-serif;
    outline: none;
}

QMainWindow, QDialog {
    background-color: #0d1117;
}

QWidget {
    background-color: transparent;
    color: #e6edf3;
    selection-background-color: #1f6feb;
    selection-color: #fff;
}

/* ── Sidebar ──────────────────────────────── */
#sidebar {
    background-color: #010409;
    border-right: 1px solid #21262d;
    min-width: 210px;
    max-width: 210px;
}

#app_icon {
    font-size: 22px;
    padding: 0;
    color: #00ff88;
    background: transparent;
    border: none;
}

#app_title {
    color: #00ff88;
    font-size: 14px;
    font-weight: bold;
    letter-spacing: 3px;
    background: transparent;
    border: none;
}

#app_subtitle {
    color: #3fb950;
    font-size: 9px;
    letter-spacing: 2px;
    background: transparent;
    border: none;
}

/* ── Nav buttons ──────────────────────────── */
QPushButton#nav_btn {
    background: transparent;
    border: none;
    border-left: 3px solid transparent;
    border-radius: 0;
    color: #7d8590;
    text-align: left;
    padding: 11px 20px;
    font-size: 13px;
    margin: 0;
}

QPushButton#nav_btn:hover {
    background-color: rgba(0, 255, 136, 0.05);
    color: #c9d1d9;
    border-left: 3px solid #30363d;
}

QPushButton#nav_btn[active="true"] {
    background-color: rgba(0, 255, 136, 0.08);
    color: #00ff88;
    border-left: 3px solid #00ff88;
    font-weight: 600;
}

/* ── Top bar ──────────────────────────────── */
#topbar {
    background-color: #010409;
    border-bottom: 1px solid #21262d;
    min-height: 58px;
    max-height: 58px;
}

/* ── Stat cards in topbar ─────────────────── */
#stat_mini {
    background: rgba(255,255,255,0.03);
    border: 1px solid #21262d;
    border-radius: 8px;
    padding: 6px 14px;
}

/* ── Device card ──────────────────────────── */
#device_card {
    background-color: #161b22;
    border: 1px solid #21262d;
    border-left: 3px solid #21262d;
    border-radius: 10px;
}

#device_card[status="online"] {
    border-left: 3px solid #3fb950;
}

#device_card[status="offline"] {
    border-left: 3px solid #6e4040;
    opacity: 0.6;
}

#device_card:hover {
    border-color: #30363d;
    border-left-color: inherit;
}

/* ── Metric area inside card ──────────────── */
#metric_box {
    background-color: #0d1117;
    border: 1px solid #21262d;
    border-radius: 7px;
}

/* ── GPU chip ─────────────────────────────── */
#gpu_chip {
    background-color: #0d1117;
    border: 1px solid #30363d;
    border-radius: 6px;
}

/* ── Labels ───────────────────────────────── */
QLabel#val_xl {
    color: #00ff88;
    font-size: 28px;
    font-weight: bold;
    letter-spacing: 1px;
}

QLabel#val_lg {
    color: #00ff88;
    font-size: 20px;
    font-weight: bold;
}

QLabel#val_md {
    color: #e6edf3;
    font-size: 14px;
    font-weight: 600;
}

QLabel#lbl_muted {
    color: #7d8590;
    font-size: 10px;
    letter-spacing: 1px;
}

QLabel#lbl_sub {
    color: #7d8590;
    font-size: 11px;
}

QLabel#lbl_hostname {
    color: #e6edf3;
    font-size: 13px;
    font-weight: bold;
}

QLabel#badge_on {
    background-color: rgba(63, 185, 80, 0.15);
    color: #3fb950;
    border: 1px solid rgba(63, 185, 80, 0.4);
    border-radius: 10px;
    padding: 2px 8px;
    font-size: 10px;
    font-weight: bold;
}

QLabel#badge_off {
    background-color: rgba(110, 64, 64, 0.3);
    color: #f85149;
    border: 1px solid rgba(248, 81, 73, 0.3);
    border-radius: 10px;
    padding: 2px 8px;
    font-size: 10px;
    font-weight: bold;
}

QLabel#section_header {
    color: #7d8590;
    font-size: 10px;
    font-weight: bold;
    letter-spacing: 2px;
    padding-bottom: 6px;
    border-bottom: 1px solid #21262d;
}

/* ── Progress bars ────────────────────────── */
QProgressBar {
    background-color: #21262d;
    border: none;
    border-radius: 3px;
    height: 5px;
    text-align: right;
    color: transparent;
}

QProgressBar#cpu_bar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #388bfd, stop:1 #58a6ff);
    border-radius: 3px;
}

QProgressBar#ram_bar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #7c3aed, stop:1 #a78bfa);
    border-radius: 3px;
}

QProgressBar#gpu_bar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #d47521, stop:1 #f0883e);
    border-radius: 3px;
}

QProgressBar#gpu_bar_hot::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #c0392b, stop:1 #f85149);
    border-radius: 3px;
}

/* ── Buttons ──────────────────────────────── */
QPushButton {
    background-color: #21262d;
    border: 1px solid #30363d;
    border-radius: 6px;
    color: #c9d1d9;
    padding: 6px 14px;
    font-size: 12px;
    font-weight: 500;
}

QPushButton:hover {
    background-color: #30363d;
    border-color: #8b949e;
    color: #e6edf3;
}

QPushButton:pressed {
    background-color: #161b22;
}

QPushButton:disabled {
    color: #484f58;
    border-color: #21262d;
}

QPushButton#btn_green {
    background-color: rgba(63, 185, 80, 0.08);
    border-color: rgba(63, 185, 80, 0.4);
    color: #3fb950;
}

QPushButton#btn_green:hover {
    background-color: rgba(63, 185, 80, 0.18);
    border-color: #3fb950;
    color: #56d36e;
}

QPushButton#btn_red {
    background-color: transparent;
    border-color: rgba(248, 81, 73, 0.3);
    color: #f85149;
}

QPushButton#btn_red:hover {
    background-color: rgba(248, 81, 73, 0.1);
    border-color: #f85149;
}

QPushButton#btn_blue {
    background-color: rgba(88, 166, 255, 0.08);
    border-color: rgba(88, 166, 255, 0.35);
    color: #58a6ff;
}

QPushButton#btn_blue:hover {
    background-color: rgba(88, 166, 255, 0.16);
    border-color: #58a6ff;
}

QPushButton#btn_icon {
    background: transparent;
    border: 1px solid #30363d;
    border-radius: 6px;
    color: #7d8590;
    padding: 5px 8px;
    font-size: 14px;
}

QPushButton#btn_icon:hover {
    border-color: #8b949e;
    color: #e6edf3;
    background: #21262d;
}

/* ── Line edits ───────────────────────────── */
QLineEdit, QComboBox {
    background-color: #0d1117;
    border: 1px solid #30363d;
    border-radius: 6px;
    color: #e6edf3;
    padding: 8px 12px;
    font-size: 12px;
}

QLineEdit:focus, QComboBox:focus {
    border-color: #00ff88;
}

QLineEdit::placeholder {
    color: #484f58;
}

QComboBox::drop-down {
    border: none;
    width: 28px;
}

QComboBox::down-arrow {
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid #7d8590;
    width: 0; height: 0;
    margin-right: 8px;
}

QComboBox QAbstractItemView {
    background-color: #161b22;
    border: 1px solid #30363d;
    selection-background-color: #21262d;
    color: #e6edf3;
    outline: none;
    padding: 4px;
}

/* ── Scrollbars ───────────────────────────── */
QScrollBar:vertical {
    background: transparent;
    width: 6px;
    margin: 0;
}

QScrollBar::handle:vertical {
    background: #30363d;
    border-radius: 3px;
    min-height: 40px;
}

QScrollBar::handle:vertical:hover {
    background: #484f58;
}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    height: 0;
}

QScrollBar:horizontal {
    background: transparent;
    height: 6px;
}

QScrollBar::handle:horizontal {
    background: #30363d;
    border-radius: 3px;
    min-width: 40px;
}

/* ── Separators ───────────────────────────── */
QFrame[frameShape="4"],
QFrame[frameShape="5"] {
    border: none;
    background: #21262d;
    max-height: 1px;
    max-width: 1px;
}

/* ── Status bar ───────────────────────────── */
QStatusBar {
    background: #010409;
    color: #484f58;
    border-top: 1px solid #21262d;
    font-size: 11px;
    padding: 3px 10px;
}

/* ── Tooltips ─────────────────────────────── */
QToolTip {
    background-color: #161b22;
    color: #e6edf3;
    border: 1px solid #30363d;
    border-radius: 4px;
    padding: 4px 8px;
    font-size: 11px;
}

/* ── Scroll area ──────────────────────────── */
QScrollArea {
    border: none;
    background: transparent;
}

/* ── Info box ─────────────────────────────── */
#info_box {
    background-color: rgba(0, 255, 136, 0.05);
    border: 1px solid rgba(0, 255, 136, 0.2);
    border-radius: 8px;
}

#warn_box {
    background-color: rgba(210, 153, 34, 0.07);
    border: 1px solid rgba(210, 153, 34, 0.3);
    border-radius: 8px;
}

/* ── Settings card ────────────────────────── */
#settings_card {
    background-color: #161b22;
    border: 1px solid #21262d;
    border-radius: 10px;
}
"""
