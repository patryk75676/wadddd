#!/bin/bash
set -e

echo ""
echo " ╔══════════════════════════════════════════════╗"
echo " ║   Mining Farm Manager — Build (Dashboard)    ║"
echo " ╚══════════════════════════════════════════════╝"
echo ""

SRC="$(cd "$(dirname "$0")" && pwd)"
BUILD="$SRC/build_tmp"
DIST="$SRC/dist"

rm -rf "$BUILD"
mkdir -p "$BUILD" "$DIST"

echo " [1/4] Instaluję narzędzia..."
pip3 install pyarmor nuitka pyinstaller ordered-set zstandard --quiet

echo " [2/4] Kopiuję źródła..."
cp -r "$SRC"/*.py "$BUILD/"
cp -r "$SRC/ui"   "$BUILD/ui"
cp -r "$SRC/agent" "$BUILD/agent"

echo " [3/4] PyArmor — szyfrowanie bytecode..."
cd "$BUILD"
pyarmor gen --output pyarmor_dist --recursive .
cp -r pyarmor_dist/. .
rm -rf pyarmor_dist

echo " [4/4] Nuitka — kompilacja do natywnego kodu..."
python3 -m nuitka \
    --onefile \
    --standalone \
    --output-dir="$DIST" \
    --output-filename="MiningFarmManager" \
    --include-package=ui \
    --include-package=PyQt6 \
    --include-package=flask \
    --include-package=psutil \
    --include-package=requests \
    --enable-plugin=pyqt6 \
    --assume-yes-for-downloads \
    main.py \
|| {
    echo " [WARN] Nuitka nieudany — próbuję PyInstaller..."
    pyinstaller \
        --onefile \
        --name "MiningFarmManager" \
        --distpath "$DIST" \
        --workpath "$BUILD/pyinst_work" \
        --specpath "$BUILD" \
        --add-data "ui:ui" \
        main.py
}

rm -rf "$BUILD"

echo ""
echo " ✓ Gotowe!  Plik: $DIST/MiningFarmManager"
echo ""
