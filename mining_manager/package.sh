#!/bin/bash
set -e

echo ""
echo " ╔══════════════════════════════════════════════════╗"
echo " ║   Mining Farm Manager — Pakowanie wydania        ║"
echo " ╚══════════════════════════════════════════════════╝"
echo ""
echo " Tworzy folder release/ z dwoma wersjami:"
echo "   source/    — kod źródłowy (Python, do developmentu)"
echo "   compiled/  — skompilowany + zaszyfrowany (do produkcji)"
echo ""

SRC="$(cd "$(dirname "$0")" && pwd)"
RELEASE="$SRC/release"
SRC_OUT="$RELEASE/source"
BLD_OUT="$RELEASE/compiled"
BUILD_TMP="$SRC/build_tmp"

# ── Sprzątanie ──────────────────────────────────────────────────────────
rm -rf "$RELEASE" "$BUILD_TMP"
mkdir -p "$SRC_OUT/dashboard" "$SRC_OUT/agent" \
         "$BLD_OUT/dashboard" "$BLD_OUT/agent" \
         "$BUILD_TMP"

# ════════════════════════════════════════════════════════════════════════
# WERSJA ŹRÓDŁOWA (source)
# ════════════════════════════════════════════════════════════════════════
echo " [1/6] Kopiuję kod źródłowy dashboardu..."
cp "$SRC/main.py" "$SRC/state.py" "$SRC/server.py" "$SRC/requirements.txt" \
   "$SRC_OUT/dashboard/"
cp -r "$SRC/ui" "$SRC_OUT/dashboard/ui"

echo " [2/6] Kopiuję kod źródłowy agenta..."
cp "$SRC/agent/agent.py" \
   "$SRC/agent/hardware_detect.py" \
   "$SRC/agent/wol_setup.py" \
   "$SRC/agent/install_linux.sh" \
   "$SRC_OUT/agent/"
# Windows installer included for cross-platform completeness
cp "$SRC/agent/install_windows.bat" "$SRC_OUT/agent/" 2>/dev/null || true

cat > "$SRC_OUT/INSTALACJA_ZRODLA.md" << 'EOF'
# Uruchomienie ze źródeł

## Dashboard
```
pip install PyQt6 Flask psutil requests
cd source/dashboard
python main.py
```

## Agent (na maszynach kopalni)
```
pip install psutil requests
cd source/agent
# Edytuj agent.env i wpisz dane serwera, poolu i portfela
# Następnie uruchom instalator:
bash install_linux.sh
```
EOF

# ════════════════════════════════════════════════════════════════════════
# WERSJA SKOMPILOWANA (compiled)
# ════════════════════════════════════════════════════════════════════════
if ! command -v python3 &>/dev/null; then
    echo " [ERR] Python3 nie znaleziony — nie można skompilować wersji compiled"
    echo " Wersja source jest gotowa w: $SRC_OUT"
    exit 1
fi

echo " [3/6] Instaluję narzędzia (PyArmor, Nuitka, PyInstaller)..."
pip3 install pyarmor nuitka pyinstaller PyQt6 Flask psutil requests \
    ordered-set zstandard --quiet

# ── Budowanie dashboardu ────────────────────────────────────────────────
echo " [4/6] Budowanie dashboardu (PyArmor + Nuitka)..."
mkdir -p "$BUILD_TMP/dashboard"
cp "$SRC"/*.py "$BUILD_TMP/dashboard/"
cp -r "$SRC/ui" "$BUILD_TMP/dashboard/ui"

cd "$BUILD_TMP/dashboard"

# Warstwa 1 — PyArmor
if pyarmor gen --output pa_dist --recursive . >/dev/null 2>&1; then
    cp -r pa_dist/. .
    rm -rf pa_dist
fi

# Warstwa 2 — Nuitka → binary
if ! python3 -m nuitka \
        --onefile \
        --standalone \
        --output-dir="$BLD_OUT/dashboard" \
        --output-filename="MiningFarmManager" \
        --include-package=ui \
        --include-package=PyQt6 \
        --include-package=flask \
        --include-package=psutil \
        --include-package=requests \
        --enable-plugin=pyqt6 \
        --assume-yes-for-downloads \
        main.py >/dev/null 2>&1; then
    echo " [WARN] Nuitka nieudana — używam PyInstaller dla dashboardu..."
    pyinstaller \
        --onefile \
        --name "MiningFarmManager" \
        --distpath "$BLD_OUT/dashboard" \
        --workpath "$BUILD_TMP/pyinst_d" \
        --specpath "$BUILD_TMP" \
        --add-data "ui:ui" \
        main.py >/dev/null 2>&1
fi

# ── Budowanie agenta ────────────────────────────────────────────────────
echo " [5/6] Budowanie agenta (PyArmor + Nuitka)..."
mkdir -p "$BUILD_TMP/agent"
cp "$SRC/agent/agent.py" \
   "$SRC/agent/hardware_detect.py" \
   "$SRC/agent/wol_setup.py" \
   "$BUILD_TMP/agent/"

cd "$BUILD_TMP/agent"

# Warstwa 1 — PyArmor
if pyarmor gen --output pa_dist agent.py hardware_detect.py wol_setup.py >/dev/null 2>&1; then
    cp -r pa_dist/. .
    rm -rf pa_dist
fi

# Warstwa 2 — Nuitka → binary
if ! python3 -m nuitka \
        --onefile \
        --standalone \
        --output-dir="$BLD_OUT/agent" \
        --output-filename="agent" \
        --include-package=psutil \
        --include-package=requests \
        --assume-yes-for-downloads \
        agent.py >/dev/null 2>&1; then
    echo " [WARN] Nuitka nieudana — używam PyInstaller dla agenta..."
    pyinstaller \
        --onefile \
        --name "agent" \
        --distpath "$BLD_OUT/agent" \
        --workpath "$BUILD_TMP/pyinst_a" \
        --specpath "$BUILD_TMP" \
        agent.py >/dev/null 2>&1
fi

# Skopiuj instalatory do compiled/agent
cp "$SRC/agent/install_linux.sh" "$BLD_OUT/agent/"
cp "$SRC/agent/install_windows.bat" "$BLD_OUT/agent/" 2>/dev/null || true
chmod +x "$BLD_OUT/agent/install_linux.sh"

cat > "$BLD_OUT/INSTALACJA_COMPILED.md" << 'EOF'
# Instalacja — wersja skompilowana

## Dashboard (Twój komputer)
```
compiled/dashboard/MiningFarmManager
```
Nie wymaga instalacji Pythona.

## Agent (maszyny kopalni)
1. Skopiuj folder `compiled/agent/` na maszynę kopalni
2. Uruchom jako root:
   ```
   bash install_linux.sh
   ```
Agent zostanie zainstalowany jako usługa systemd.
Nie wymaga instalacji Pythona na maszynie kopalni.
EOF

# ── Sprzątanie ──────────────────────────────────────────────────────────
echo " [6/6] Czyszczę pliki tymczasowe..."
cd "$SRC"
rm -rf "$BUILD_TMP"

# ── Podsumowanie ────────────────────────────────────────────────────────
echo ""
echo " ════════════════════════════════════════════════════"
echo "  Wydanie gotowe w: $RELEASE"
echo " ════════════════════════════════════════════════════"
echo ""
echo "  release/"
echo "  ├── source/"
echo "  │   ├── dashboard/    ← kod źródłowy dashboardu (Python)"
echo "  │   ├── agent/        ← kod źródłowy agenta (Python)"
echo "  │   └── INSTALACJA_ZRODLA.md"
echo "  └── compiled/"
echo "      ├── dashboard/    ← MiningFarmManager (zaszyfrowany)"
echo "      ├── agent/        ← agent + install_linux.sh"
echo "      └── INSTALACJA_COMPILED.md"
echo ""
