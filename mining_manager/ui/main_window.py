import socket
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QLabel, QStackedWidget, QFrame, QSizePolicy,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont

from state import STATE
from ui.pages.machines import MachinesPage
from ui.pages.settings import SettingsPage


def _local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def fmt_hr(hs: float) -> str:
    if hs >= 1e9: return f"{hs/1e9:.2f} GH/s"
    if hs >= 1e6: return f"{hs/1e6:.2f} MH/s"
    if hs >= 1e3: return f"{hs/1e3:.2f} kH/s"
    return f"{hs:.1f} H/s"


class Sidebar(QFrame):
    def __init__(self, stack: QStackedWidget):
        super().__init__()
        self.setObjectName("sidebar")
        self._stack = stack
        self._btns: list[QPushButton] = []
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Logo block
        logo_w = QWidget()
        logo_w.setFixedHeight(82)
        logo_w.setStyleSheet("background:transparent;")
        ll = QVBoxLayout(logo_w)
        ll.setContentsMargins(20, 18, 20, 10)
        ll.setSpacing(2)

        icon = QLabel("⛏")
        icon.setObjectName("app_icon")
        title = QLabel("MINING")
        title.setObjectName("app_title")
        sub = QLabel("FARM MANAGER")
        sub.setObjectName("app_subtitle")

        ll.addWidget(icon)
        ll.addWidget(title)
        ll.addWidget(sub)
        layout.addWidget(logo_w)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFixedHeight(1)
        layout.addWidget(sep)
        layout.addSpacing(6)

        # Nav items
        nav_items = [
            ("🖥   Maszyny", 0),
            ("⚙   Ustawienia", 1),
        ]

        for label, idx in nav_items:
            btn = QPushButton(label)
            btn.setObjectName("nav_btn")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda c=False, i=idx: self._select(i))
            layout.addWidget(btn)
            self._btns.append(btn)

        layout.addStretch()

        # Version tag
        ver = QLabel("v3.0")
        ver.setObjectName("lbl_muted")
        ver.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ver.setContentsMargins(0, 0, 0, 14)
        layout.addWidget(ver)

        self._select(0)

    def _select(self, idx: int):
        for i, btn in enumerate(self._btns):
            active = "true" if i == idx else "false"
            btn.setProperty("active", active)
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        self._stack.setCurrentIndex(idx)


class TopBar(QFrame):
    def __init__(self):
        super().__init__()
        self.setObjectName("topbar")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(24, 0, 24, 0)
        layout.setSpacing(0)

        # Total hashrate
        hr_w = QWidget()
        hr_w.setStyleSheet("background:transparent;")
        hr_l = QVBoxLayout(hr_w)
        hr_l.setContentsMargins(0, 0, 0, 0)
        hr_l.setSpacing(1)
        self.lbl_hr = QLabel("0 H/s")
        self.lbl_hr.setObjectName("val_lg")
        lbl_hr_t = QLabel("ŁĄCZNY HASHRATE")
        lbl_hr_t.setObjectName("lbl_muted")
        hr_l.addWidget(self.lbl_hr)
        hr_l.addWidget(lbl_hr_t)
        layout.addWidget(hr_w)

        layout.addSpacing(32)

        # Online / offline
        for attr, label_txt, color in [
            ("lbl_online", "ONLINE", "#3fb950"),
            ("lbl_offline", "OFFLINE", "#f85149"),
        ]:
            w = QWidget()
            w.setStyleSheet("background:transparent;")
            wl = QVBoxLayout(w)
            wl.setContentsMargins(0, 0, 0, 0)
            wl.setSpacing(1)
            val = QLabel("0")
            val.setObjectName("val_lg")
            val.setStyleSheet(f"color:{color};")
            lbl = QLabel(label_txt)
            lbl.setObjectName("lbl_muted")
            wl.addWidget(val)
            wl.addWidget(lbl)
            layout.addWidget(w)
            setattr(self, attr, val)
            layout.addSpacing(24)

        layout.addStretch()

        # Server info badge
        self.lbl_srv = QLabel("⚡  serwer: —")
        self.lbl_srv.setObjectName("lbl_muted")
        layout.addWidget(self.lbl_srv)

    def update(self, total_hr: float, online: int, offline: int, ip: str):
        self.lbl_hr.setText(fmt_hr(total_hr))
        self.lbl_online.setText(str(online))
        self.lbl_offline.setText(str(offline))
        self.lbl_srv.setText(f"⚡  {ip}:8000")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Mining Farm Manager")
        self.setMinimumSize(960, 660)
        self.resize(1280, 820)
        self._ip = _local_ip()
        self._build_ui()
        self._start_timer()

    def _build_ui(self):
        central = QWidget()
        central.setStyleSheet("background:#0d1117;")
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Top bar
        self.topbar = TopBar()
        root.addWidget(self.topbar)

        # Content row
        content = QHBoxLayout()
        content.setContentsMargins(0, 0, 0, 0)
        content.setSpacing(0)

        # Pages stack
        self._stack = QStackedWidget()
        self._stack.setStyleSheet("background:#0d1117;")

        self._page_machines = MachinesPage()
        self._page_settings = SettingsPage()

        self._stack.addWidget(self._page_machines)
        self._stack.addWidget(self._page_settings)

        # Sidebar
        self._sidebar = Sidebar(self._stack)
        content.addWidget(self._sidebar)
        content.addWidget(self._stack, 1)

        root.addLayout(content, 1)

        # Status bar
        self.statusBar().showMessage(
            f"  Serwer nasłuchuje na {self._ip}:8000  "
            f"  Agenty: RM_SERVER_URL=http://{self._ip}:8000"
        )

    def _start_timer(self):
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh)
        self._timer.start(2000)
        self._refresh()

    def _refresh(self):
        s = STATE.summary()
        self.topbar.update(
            s["total_hr"],
            s["online"],
            s["total"] - s["online"],
            self._ip,
        )
        page = self._stack.currentWidget()
        if hasattr(page, "refresh"):
            page.refresh()
