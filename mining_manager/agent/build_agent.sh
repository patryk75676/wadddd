#!/bin/bash
set -e

echo ""
echo " ╔══════════════════════════════════════════════╗"
echo " ║   Mining Farm Manager — Build (Agent)        ║"
echo " ╚══════════════════════════════════════════════╝"
echo ""

SRC="$(cd "$(dirname "$0")" && pwd)"
BUILD="$SRC/build_tmp"
DIST="$SRC/dist"

rm -rf "$BUILD"
mkdir -p "$BUILD" "$DIST"

echo " [1/4] Instaluję narzędzia..."
pip3 install pyarmor nuitka pyinstaller psutil requests ordered-set zstandard --quiet

echo " [2/4] Kopiuję źródła agenta..."
cp "$SRC/agent.py" "$SRC/hardware_detect.py" "$SRC/wol_setup.py" "$BUILD/"

echo " [3/4] PyArmor — szyfrowanie bytecode..."
cd "$BUILD"
pyarmor gen --output pyarmor_dist agent.py hardware_detect.py wol_setup.py
cp -r pyarmor_dist/. .
rm -rf pyarmor_dist

echo " [4/4] Nuitka — kompilacja do natywnego binarnego..."
python3 -m nuitka \
    --onefile \
    --standalone \
    --output-dir="$DIST" \
    --output-filename="agent" \
    --include-package=psutil \
    --include-package=requests \
    --assume-yes-for-downloads \
    agent.py \
|| {
    echo " [WARN] Nuitka nieudana — próbuję PyInstaller..."
    pyinstaller \
        --onefile \
        --name "agent" \
        --distpath "$DIST" \
        --workpath "$BUILD/pyinst_work" \
        --specpath "$BUILD" \
        agent.py
}

rm -rf "$BUILD"
cp "$SRC/install_linux.sh" "$DIST/"

echo ""
echo " ✓ Gotowe!"
echo " ✓ Agent:      $DIST/agent"
echo " ✓ Instalator: $DIST/install_linux.sh"
echo ""
echo " Skopiuj folder $DIST/ na maszynę kopalni i uruchom install_linux.sh"
echo ""
