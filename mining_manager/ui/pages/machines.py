import time
from PyQt6.QtWidgets import (
    QWidget, QScrollArea, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QProgressBar, QSizePolicy, QMessageBox,
    QDialog, QButtonGroup,
)
from PyQt6.QtCore import Qt, QPoint, QSize
from PyQt6.QtGui import QPainter, QPen, QColor, QPolygon, QFont

from state import STATE
from ui.flow_layout import FlowLayout


def fmt_hr(hs: float) -> str:
    if not hs:
        return "0 H/s"
    if hs >= 1e9:
        return f"{hs / 1e9:.2f} GH/s"
    if hs >= 1e6:
        return f"{hs / 1e6:.2f} MH/s"
    if hs >= 1e3:
        return f"{hs / 1e3:.1f} kH/s"
    return f"{hs:.1f} H/s"


class SparklineWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.data: list[float] = []
        self.setMinimumHeight(40)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def set_data(self, data: list[float]):
        self.data = data[-80:]
        self.update()

    def paintEvent(self, event):
        if len(self.data) < 2:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        mn, mx = min(self.data), max(self.data)
        if mx == mn:
            mx = mn + 1

        def pt(i, v):
            x = int(i / (len(self.data) - 1) * (w - 2)) + 1
            y = int((1 - (v - mn) / (mx - mn)) * (h - 8)) + 4
            return QPoint(x, y)

        pts = [pt(i, v) for i, v in enumerate(self.data)]

        fill = QPolygon([QPoint(1, h - 1)] + pts + [QPoint(w - 1, h - 1)])
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(0, 255, 136, 18))
        p.drawPolygon(fill)

        pen = QPen(QColor("#00ff88"), 1.5)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        for i in range(1, len(pts)):
            p.drawLine(pts[i - 1], pts[i])

        # Last value dot
        if pts:
            p.setBrush(QColor("#00ff88"))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(pts[-1], 3, 3)


class GpuChip(QFrame):
    def __init__(self, gpu: dict, parent=None):
        super().__init__(parent)
        self.setObjectName("gpu_chip")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(3)

        name = (gpu.get("name") or "GPU")[:18]
        name_lbl = QLabel(name)
        name_lbl.setStyleSheet(
            "color:#58a6ff;font-size:10px;font-weight:bold;"
            "background:transparent;border:none;"
        )
        layout.addWidget(name_lbl)

        load = float(gpu.get("load") or 0)
        temp = int(gpu.get("temp_c") or 0)
        info = QLabel(f"{load:.0f}%  ·  {temp}°C")
        info.setStyleSheet(
            "color:#7d8590;font-size:10px;background:transparent;border:none;"
        )
        layout.addWidget(info)

        bar = QProgressBar()
        bar.setMaximum(100)
        bar.setValue(int(load))
        bar.setTextVisible(False)
        bar.setFixedHeight(3)
        color = "#f85149" if temp > 82 else "#f0883e" if temp > 70 else "#3fb950"
        bar.setStyleSheet(
            f"QProgressBar{{background:#21262d;border:none;border-radius:1px;}}"
            f"QProgressBar::chunk{{background:{color};border-radius:1px;}}"
        )
        layout.addWidget(bar)


def _fmt_remaining(sched: dict) -> str:
    stop_at = sched.get("stop_at")
    if not stop_at:
        return "∞  Non-stop"
    remaining = max(0, stop_at - time.time())
    h = int(remaining // 3600)
    m = int((remaining % 3600) // 60)
    s = int(remaining % 60)
    return f"⏱  {h:02d}:{m:02d}:{s:02d}"


class ScheduleDialog(QDialog):
    OPTS = [
        ("1 godzina",  1),
        ("6 godzin",   6),
        ("12 godzin", 12),
        ("24 godziny", 24),
        ("48 godzin",  48),
        ("Non-stop",    0),
    ]

    def __init__(self, device_id: str, hostname: str, parent=None):
        super().__init__(parent)
        self.device_id = device_id
        self.chosen_hours: float | None = None
        self.setWindowTitle(f"Harmonogram — {hostname}")
        self.setModal(True)
        self.setFixedWidth(300)
        self.setStyleSheet(
            "QDialog{background:#161b22;color:#e6edf3;border:1px solid #30363d;border-radius:10px;}"
            "QLabel{background:transparent;color:#e6edf3;}"
        )
        self._build_ui(hostname)

    def _build_ui(self, hostname: str):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 18)
        root.setSpacing(10)

        title = QLabel(f"⏱  Kopaj przez…")
        title.setStyleSheet("font-size:14px;font-weight:bold;color:#e6edf3;")
        root.addWidget(title)

        sub = QLabel(f"Maszyna: <b style='color:#58a6ff'>{hostname}</b>")
        sub.setStyleSheet("color:#7d8590;font-size:11px;")
        root.addWidget(sub)

        for label, hours in self.OPTS:
            btn = QPushButton(label)
            btn.setStyleSheet(
                "QPushButton{background:#21262d;border:1px solid #30363d;border-radius:6px;"
                "color:#e6edf3;padding:8px;font-size:12px;text-align:left;}"
                "QPushButton:hover{background:#2d333b;border-color:#58a6ff;color:#58a6ff;}"
            )
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda c=False, h=hours: self._pick(h))
            root.addWidget(btn)

        cancel = QPushButton("Anuluj")
        cancel.setStyleSheet(
            "QPushButton{background:transparent;border:1px solid #30363d;border-radius:6px;"
            "color:#7d8590;padding:6px;font-size:11px;}"
            "QPushButton:hover{border-color:#f85149;color:#f85149;}"
        )
        cancel.clicked.connect(self.reject)
        root.addWidget(cancel)

    def _pick(self, hours: float):
        self.chosen_hours = hours
        self.accept()


class DeviceCard(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("device_card")
        self.device_id: str | None = None
        self.setFixedWidth(354)
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 12, 14, 12)
        root.setSpacing(9)

        # ── Header ────────────────────────────
        hdr = QHBoxLayout()
        hdr.setSpacing(6)
        self.lbl_host = QLabel("—")
        self.lbl_host.setObjectName("lbl_hostname")
        self.lbl_status = QLabel("OFF")
        self.lbl_status.setObjectName("badge_off")
        self.lbl_status.setFixedWidth(38)
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hdr.addWidget(self.lbl_host, 1)
        hdr.addWidget(self.lbl_status)
        root.addLayout(hdr)

        self.lbl_sub = QLabel("—")
        self.lbl_sub.setObjectName("lbl_sub")
        root.addWidget(self.lbl_sub)

        # ── Hashrate ──────────────────────────
        self.lbl_hr = QLabel("0 H/s")
        self.lbl_hr.setObjectName("val_xl")
        self.lbl_hr.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(self.lbl_hr)

        self.lbl_hr_sub = QLabel("1m: —  ·  15m: —")
        self.lbl_hr_sub.setObjectName("lbl_muted")
        self.lbl_hr_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(self.lbl_hr_sub)

        # ── CPU / RAM ─────────────────────────
        metric_box = QFrame()
        metric_box.setObjectName("metric_box")
        mb_layout = QVBoxLayout(metric_box)
        mb_layout.setContentsMargins(10, 8, 10, 8)
        mb_layout.setSpacing(7)

        self.cpu_bar = self._bar("cpu_bar")
        self.ram_bar = self._bar("ram_bar")
        self.lbl_cpu = QLabel("0%")
        self.lbl_cpu.setObjectName("lbl_muted")
        self.lbl_cpu.setFixedWidth(32)
        self.lbl_cpu.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.lbl_ram = QLabel("0%")
        self.lbl_ram.setObjectName("lbl_muted")
        self.lbl_ram.setFixedWidth(32)
        self.lbl_ram.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        for bar, pct_lbl, txt in [(self.cpu_bar, self.lbl_cpu, "CPU"),
                                   (self.ram_bar, self.lbl_ram, "RAM")]:
            row = QHBoxLayout()
            row.setSpacing(6)
            l = QLabel(txt)
            l.setObjectName("lbl_muted")
            l.setFixedWidth(26)
            row.addWidget(l)
            row.addWidget(bar, 1)
            row.addWidget(pct_lbl)
            mb_layout.addLayout(row)

        root.addWidget(metric_box)

        # ── GPU row ───────────────────────────
        self.gpu_row = QHBoxLayout()
        self.gpu_row.setSpacing(5)
        root.addLayout(self.gpu_row)

        # ── Sparkline ─────────────────────────
        self.sparkline = SparklineWidget()
        root.addWidget(self.sparkline)

        # ── Shares ────────────────────────────
        self.lbl_shares = QLabel("pool: —")
        self.lbl_shares.setObjectName("lbl_muted")
        root.addWidget(self.lbl_shares)

        # ── Schedule countdown ────────────────
        self.lbl_sched = QLabel("")
        self.lbl_sched.setObjectName("lbl_muted")
        self.lbl_sched.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_sched.setStyleSheet(
            "color:#f0883e;font-size:11px;font-weight:600;background:transparent;"
        )
        self.lbl_sched.hide()
        root.addWidget(self.lbl_sched)

        # ── Buttons ───────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setSpacing(4)

        self.btn_start = self._btn("▶", "btn_green", "Start XMRig")
        self.btn_restart = self._btn("↺", "btn_icon", "Restart XMRig")
        self.btn_stop = self._btn("■", "btn_red", "Zatrzymaj XMRig")
        self.btn_sched = self._btn("⏱", "btn_icon", "Harmonogram kopania")
        self.btn_sched.setFixedWidth(34)
        self.btn_uninst = self._btn("⛔", "btn_red", "Odinstaluj agenta")
        self.btn_uninst.setFixedWidth(34)

        for b in [self.btn_start, self.btn_restart, self.btn_stop,
                  self.btn_sched, self.btn_uninst]:
            btn_row.addWidget(b)

        root.addLayout(btn_row)

    @staticmethod
    def _bar(name: str) -> QProgressBar:
        bar = QProgressBar()
        bar.setObjectName(name)
        bar.setMaximum(100)
        bar.setFixedHeight(5)
        bar.setTextVisible(False)
        return bar

    @staticmethod
    def _btn(text: str, obj_name: str, tip: str = "") -> QPushButton:
        b = QPushButton(text)
        b.setObjectName(obj_name)
        b.setToolTip(tip)
        b.setCursor(Qt.CursorShape.PointingHandCursor)
        return b

    def _set_status_badge(self, online: bool):
        obj = "badge_on" if online else "badge_off"
        txt = "ON" if online else "OFF"
        self.lbl_status.setObjectName(obj)
        self.lbl_status.setText(txt)
        self.lbl_status.style().unpolish(self.lbl_status)
        self.lbl_status.style().polish(self.lbl_status)

    def _set_card_border(self, status: str):
        self.setProperty("status", status)
        self.style().unpolish(self)
        self.style().polish(self)

    def update_device(self, dev: dict):
        did = dev["device_id"]
        self.device_id = did
        status = dev.get("status", "offline")
        online = status == "online"

        hostname = dev.get("hostname") or did
        self.lbl_host.setText(f"🖥  {hostname}")
        platform = dev.get("platform") or ""
        cpu_c = dev.get("cpu_count") or "?"
        ram = dev.get("ram_gb") or ""
        self.lbl_sub.setText(
            f"{platform}  ·  {cpu_c}× CPU"
            + (f"  ·  {ram} GB RAM" if ram else "")
        )
        self._set_status_badge(online)
        self._set_card_border(status)

        if online:
            mining = dev.get("mining") or {}
            hw = dev.get("hardware") or {}

            hr = mining.get("hashrate_hs") or 0
            hr1 = mining.get("hashrate_1m") or 0
            hr15 = mining.get("hashrate_15m") or 0
            self.lbl_hr.setText(fmt_hr(hr))
            self.lbl_hr_sub.setText(f"1m: {fmt_hr(hr1)}  ·  15m: {fmt_hr(hr15)}")

            cpu = float(hw.get("cpu_percent") or 0)
            ram_pct = float(hw.get("ram_percent") or 0)
            self.cpu_bar.setValue(int(cpu))
            self.ram_bar.setValue(int(ram_pct))
            self.lbl_cpu.setText(f"{cpu:.0f}%")
            self.lbl_ram.setText(f"{ram_pct:.0f}%")

            # GPU chips
            while self.gpu_row.count():
                item = self.gpu_row.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            gpus = hw.get("gpus") or []
            for gpu in gpus[:4]:
                self.gpu_row.addWidget(GpuChip(gpu))
            if not gpus:
                self.gpu_row.addStretch()

            # Sparkline
            hist = STATE.get_history(did, 80)
            self.sparkline.set_data([h["hr"] for h in hist])

            # Shares
            acc = mining.get("accepted") or 0
            rej = mining.get("rejected") or 0
            pool = (mining.get("pool") or "").split(".")[0] or "—"
            algo = mining.get("algo") or ""
            self.lbl_shares.setText(
                f"✓ {acc}  ✗ {rej}  ·  {pool}"
                + (f"  ·  {algo}" if algo else "")
            )
        else:
            self.lbl_hr.setText("offline")
            self.lbl_hr.setStyleSheet("color: #484f58;")

        # Schedule countdown
        sched = STATE.get_schedule(did)
        if sched:
            self.lbl_sched.setText(_fmt_remaining(sched))
            self.lbl_sched.show()
        else:
            self.lbl_sched.hide()

        # Reconnect buttons
        for btn in [self.btn_start, self.btn_stop, self.btn_restart,
                    self.btn_sched, self.btn_uninst]:
            try:
                btn.clicked.disconnect()
            except Exception:
                pass

        hn = hostname
        self.btn_start.clicked.connect(lambda: STATE.command(did, {"action": "start"}))
        self.btn_stop.clicked.connect(lambda: (
            STATE.cancel_schedule(did), STATE.command(did, {"action": "stop"})
        ))
        self.btn_restart.clicked.connect(lambda: STATE.command(did, {"action": "restart"}))
        self.btn_sched.clicked.connect(lambda: self._open_schedule(did, hn))
        self.btn_uninst.clicked.connect(lambda: self._ask_uninstall(did, hn))

    def _open_schedule(self, device_id: str, hostname: str):
        dlg = ScheduleDialog(device_id, hostname, self)
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.chosen_hours is not None:
            STATE.set_schedule(device_id, dlg.chosen_hours)

    def _ask_uninstall(self, device_id: str, hostname: str):
        dlg = QMessageBox(self)
        dlg.setWindowTitle("Odinstalowanie agenta")
        dlg.setText(
            f"<b>Odinstalować agenta z maszyny <span style='color:#f0883e'>{hostname}</span>?</b><br><br>"
            "Agent zatrzyma XMRig, usunie usługę systemową i wszystkie pliki.<br>"
            "<span style='color:#f85149'>Operacja jest nieodwracalna.</span>"
        )
        dlg.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        dlg.setDefaultButton(QMessageBox.StandardButton.No)
        dlg.setStyleSheet(
            "QMessageBox{background:#161b22;color:#e6edf3;}"
            "QPushButton{background:#21262d;border:1px solid #30363d;"
            "border-radius:6px;color:#e6edf3;padding:6px 18px;}"
            "QPushButton:hover{border-color:#f85149;color:#f85149;}"
        )
        if dlg.exec() == QMessageBox.StandardButton.Yes:
            STATE.command(device_id, {"action": "uninstall"})


class MachinesPage(QWidget):
    def __init__(self):
        super().__init__()
        self._cards: dict[str, DeviceCard] = {}
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 20)
        root.setSpacing(12)

        # ── Broadcast toolbar ─────────────────
        toolbar = QHBoxLayout()
        toolbar.setSpacing(6)

        lbl = QLabel("BROADCAST →")
        lbl.setObjectName("lbl_muted")
        toolbar.addWidget(lbl)

        for label, action, obj in [
            ("▶  Start wszystkie", "start", "btn_green"),
            ("■  Stop", "stop", "btn_red"),
            ("↺  Restart", "restart", ""),
        ]:
            btn = QPushButton(label)
            btn.setObjectName(obj)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda c=False, a=action: STATE.broadcast({"action": a}))
            toolbar.addWidget(btn)

        sched_all_btn = QPushButton("⏱  Harmonogram")
        sched_all_btn.setObjectName("btn_icon")
        sched_all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        sched_all_btn.setToolTip("Ustaw harmonogram kopania dla WSZYSTKICH maszyn")
        sched_all_btn.clicked.connect(self._open_schedule_all)
        toolbar.addWidget(sched_all_btn)

        toolbar.addStretch()
        self.lbl_count = QLabel("")
        self.lbl_count.setObjectName("lbl_muted")
        toolbar.addWidget(self.lbl_count)
        root.addLayout(toolbar)

        # ── Scroll area ───────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._grid_w = QWidget()
        self._grid_w.setStyleSheet("background:transparent;")
        self._flow = FlowLayout(self._grid_w, h_spacing=10, v_spacing=10)

        scroll.setWidget(self._grid_w)
        root.addWidget(scroll)

    def _open_schedule_all(self):
        dlg = ScheduleDialog("_all", "WSZYSTKIE MASZYNY", self)
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.chosen_hours is not None:
            STATE.set_schedule("_all", dlg.chosen_hours)

    def refresh(self):
        devices = STATE.get_devices()
        seen = set()

        for dev in devices:
            did = dev["device_id"]
            seen.add(did)
            if did not in self._cards:
                card = DeviceCard()
                self._cards[did] = card
                self._flow.addWidget(card)
            self._cards[did].update_device(dev)

        for did in list(self._cards):
            if did not in seen:
                card = self._cards.pop(did)
                self._flow.removeWidget(card)
                card.deleteLater()

        online = sum(1 for d in devices if d.get("status") == "online")
        total = len(devices)
        self.lbl_count.setText(
            f"{online} online  ·  {total - online} offline  ·  {total} łącznie"
        )
        self._grid_w.update()
