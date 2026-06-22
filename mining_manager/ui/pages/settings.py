import socket
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QFrame, QComboBox, QScrollArea,
)
from PyQt6.QtCore import Qt

from state import STATE


def _local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def _card(parent=None) -> QFrame:
    f = QFrame(parent)
    f.setObjectName("settings_card")
    return f


def _sep() -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.Shape.HLine)
    f.setFixedHeight(1)
    return f


def _section(title: str) -> QLabel:
    l = QLabel(title)
    l.setObjectName("section_header")
    return l


class SettingsPage(QWidget):
    def __init__(self):
        super().__init__()
        self._ip = _local_ip()
        self._build_ui()

    def _build_ui(self):
        # Scrollable content
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        container = QWidget()
        container.setStyleSheet("background:transparent;")
        root = QVBoxLayout(container)
        root.setContentsMargins(24, 20, 24, 24)
        root.setSpacing(16)

        # ══ Mining config ══════════════════════
        root.addWidget(_section("⛏  KONFIGURACJA KOPANIA"))

        mine_card = _card()
        ml = QVBoxLayout(mine_card)
        ml.setContentsMargins(18, 14, 18, 14)
        ml.setSpacing(12)

        # Pool
        pool_row = QHBoxLayout()
        pool_lbl = QLabel("Pool:")
        pool_lbl.setObjectName("lbl_muted")
        pool_lbl.setFixedWidth(72)
        self.pool_inp = QLineEdit()
        self.pool_inp.setPlaceholderText("pool.supportxmr.com:3333")
        self.pool_inp.setText(STATE.pool_url)
        pool_row.addWidget(pool_lbl)
        pool_row.addWidget(self.pool_inp)
        ml.addLayout(pool_row)

        # Wallet
        wallet_row = QHBoxLayout()
        wallet_lbl = QLabel("Portfel:")
        wallet_lbl.setObjectName("lbl_muted")
        wallet_lbl.setFixedWidth(72)
        self.wallet_inp = QLineEdit()
        self.wallet_inp.setPlaceholderText("Adres portfela XMR (monero)…")
        self.wallet_inp.setText(STATE.wallet)
        wallet_row.addWidget(wallet_lbl)
        wallet_row.addWidget(self.wallet_inp)
        ml.addLayout(wallet_row)

        # Coin
        coin_row = QHBoxLayout()
        coin_lbl = QLabel("Moneta:")
        coin_lbl.setObjectName("lbl_muted")
        coin_lbl.setFixedWidth(72)
        self.coin_combo = QComboBox()
        self.coin_combo.addItems([
            "Monero (XMR)  —  pool.supportxmr.com:3333",
            "Monero (XMR)  —  MoneroOcean (auto-switch)",
            "Monero (XMR)  —  pool.minexmr.com:443",
        ])
        self._coin_pools = [
            "pool.supportxmr.com:3333",
            "pool.moneroocean.stream:10128",
            "pool.minexmr.com:443",
        ]
        self.coin_combo.currentIndexChanged.connect(self._on_coin_change)
        coin_row.addWidget(coin_lbl)
        coin_row.addWidget(self.coin_combo)
        ml.addLayout(coin_row)

        ml.addWidget(_sep())

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        save_btn = QPushButton("💾  Zapisz")
        save_btn.setObjectName("btn_green")
        save_btn.clicked.connect(self._save)

        apply_btn = QPushButton("⚡  Zastosuj do WSZYSTKICH maszyn")
        apply_btn.setObjectName("btn_blue")
        apply_btn.clicked.connect(self._apply_all)

        btn_row.addWidget(save_btn)
        btn_row.addWidget(apply_btn)
        ml.addLayout(btn_row)

        self.lbl_mine_status = QLabel("")
        self.lbl_mine_status.setObjectName("lbl_muted")
        ml.addWidget(self.lbl_mine_status)

        root.addWidget(mine_card)

        # ══ Server info ════════════════════════
        root.addWidget(_section("🌐  INFORMACJE O SERWERZE"))

        srv_card = _card()
        srv_card.setObjectName("info_box")
        sl = QVBoxLayout(srv_card)
        sl.setContentsMargins(16, 14, 16, 14)
        sl.setSpacing(8)

        self._add_info_row(sl, "Adres serwera:", f"{self._ip}:8000", "#00ff88")
        self._add_info_row(sl, "Port:", "8000", "#58a6ff")
        self._add_info_row(sl, "Protokół:", "HTTP (tylko LAN, bez internetu)", "#7d8590")

        note = QLabel(
            f"Podczas instalacji agenta na maszynie kopalni podaj adres serwera: "
            f"<b style='color:#00ff88'>http://{self._ip}:8000</b>"
        )
        note.setStyleSheet("color:#7d8590;font-size:11px;")
        note.setWordWrap(True)
        sl.addWidget(note)
        root.addWidget(srv_card)

        # ══ Agent install guide ════════════════
        root.addWidget(_section("📋  JAK ZAINSTALOWAĆ AGENTA"))

        guide_card = _card()
        gl = QVBoxLayout(guide_card)
        gl.setContentsMargins(18, 14, 18, 14)
        gl.setSpacing(10)

        steps = [
            ("1", "Pobierz XMRig na maszynę kopalni", "#7d8590",
             "https://github.com/xmrig/xmrig/releases"),
            ("2", f"Skopiuj folder <b>agent/</b> na maszynę kopalni", "#7d8590", ""),
            ("3", "Zainstaluj Python 3.11+ i uruchom:", "#7d8590", ""),
        ]

        for num, text, color, link in steps:
            row = QHBoxLayout()
            num_lbl = QLabel(num)
            num_lbl.setStyleSheet(
                "background:#21262d;color:#7d8590;border-radius:10px;"
                "font-size:11px;font-weight:bold;padding:2px 7px;"
            )
            num_lbl.setFixedWidth(22)
            num_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            txt_lbl = QLabel(text)
            txt_lbl.setStyleSheet(f"color:{color};font-size:12px;")
            row.addWidget(num_lbl)
            row.addWidget(txt_lbl, 1)
            gl.addLayout(row)

        # Command block
        cmd_txt = (
            f"RM_SERVER_URL=http://{self._ip}:8000 \\\n"
            f"RM_POOL={STATE.pool_url or 'pool.supportxmr.com:3333'} \\\n"
            f"RM_WALLET=TWOJ_PORTFEL_XMR \\\n"
            f"python agent/agent.py"
        )
        cmd_box = QLabel(cmd_txt)
        cmd_box.setStyleSheet(
            "background:#0d1117;color:#3fb950;font-family:'Courier New',monospace;"
            "font-size:11px;padding:10px 12px;border-radius:6px;border:1px solid #21262d;"
        )
        cmd_box.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        gl.addWidget(cmd_box)

        # Windows note
        win_note = QLabel(
            "Windows: skorzystaj z <b>install_windows.bat</b> w folderze <b>agent/</b>"
        )
        win_note.setStyleSheet("color:#7d8590;font-size:11px;")
        gl.addWidget(win_note)

        root.addWidget(guide_card)
        root.addStretch()

        scroll.setWidget(container)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    def _add_info_row(self, layout, label: str, value: str, color: str):
        row = QHBoxLayout()
        lbl = QLabel(label)
        lbl.setObjectName("lbl_muted")
        lbl.setFixedWidth(130)
        val = QLabel(value)
        val.setStyleSheet(f"color:{color};font-weight:600;font-size:12px;")
        val.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        row.addWidget(lbl)
        row.addWidget(val)
        row.addStretch()
        layout.addLayout(row)

    def _on_coin_change(self, idx: int):
        pool = self._coin_pools[idx] if idx < len(self._coin_pools) else ""
        if pool:
            self.pool_inp.setText(pool)

    def _save(self):
        pool = self.pool_inp.text().strip()
        wallet = self.wallet_inp.text().strip()
        if pool:
            STATE.pool_url = pool
        if wallet:
            STATE.wallet = wallet
        self.lbl_mine_status.setText("✓ Konfiguracja zapisana lokalnie")
        self.lbl_mine_status.setStyleSheet("color:#3fb950;font-size:11px;")

    def _apply_all(self):
        pool = self.pool_inp.text().strip() or STATE.pool_url
        wallet = self.wallet_inp.text().strip()
        if not wallet:
            self.lbl_mine_status.setText("✗ Podaj adres portfela XMR")
            self.lbl_mine_status.setStyleSheet("color:#f85149;font-size:11px;")
            return
        STATE.pool_url = pool
        STATE.wallet = wallet
        n = len(STATE.devices)
        STATE.broadcast({"action": "reconfigure", "pool": pool, "wallet": wallet})
        self.lbl_mine_status.setText(f"⚡ Komenda wysłana do {n} maszyn")
        self.lbl_mine_status.setStyleSheet("color:#3fb950;font-size:11px;")

    def refresh(self):
        pass
