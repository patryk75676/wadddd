#!/bin/bash
set -e

echo ""
echo " ╔══════════════════════════════════════╗"
echo " ║     Mining Agent — Instalator        ║"
echo " ╚══════════════════════════════════════╝"
echo ""

[ "$EUID" -ne 0 ] && echo "Uruchom jako root: sudo bash install_linux.sh" && exit 1

INSTALL_DIR=/opt/mining-agent

read -p "Adres serwera (np. http://192.168.1.10:8000): " SERVER_URL
read -p "Pool (Enter = pool.supportxmr.com:3333): "      POOL
[ -z "$POOL" ] && POOL="pool.supportxmr.com:3333"
read -p "Adres portfela XMR: "                           WALLET
read -p "Ścieżka do xmrig (Enter = xmrig): "            XMRIG
[ -z "$XMRIG" ] && XMRIG="xmrig"

mkdir -p "$INSTALL_DIR"
cp agent.py wol_setup.py hardware_detect.py uninstall_protected.py "$INSTALL_DIR/"

pip3 install psutil requests --break-system-packages -q 2>/dev/null || \
pip3 install psutil requests -q

cat > /etc/mining-agent.env << ENVEOF
RM_SERVER_URL=$SERVER_URL
RM_POOL=$POOL
RM_WALLET=$WALLET
RM_XMRIG_PATH=$XMRIG
RM_INTERVAL=10
ENVEOF

cat > /etc/systemd/system/mining-agent.service << SVCEOF
[Unit]
Description=Mining Agent
After=network.target

[Service]
EnvironmentFile=/etc/mining-agent.env
ExecStart=/usr/bin/python3 $INSTALL_DIR/agent.py
Restart=always
RestartSec=15

[Install]
WantedBy=multi-user.target
SVCEOF

systemctl daemon-reload
systemctl enable mining-agent
systemctl start  mining-agent

# Pusty config — hasło ustawi się w dashboardzie
python3 -c "import json; from pathlib import Path; Path('$INSTALL_DIR/uninstall_config.json').write_text(json.dumps({'password_hash': ''}))"

echo ""
echo " ✓ Instalacja zakończona!"
echo " ✓ Dashboard: http://localhost:8000"
echo " ✓ Ustaw hasło do odinstalowania w dashboardzie"
echo ""
