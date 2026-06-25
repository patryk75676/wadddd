@echo off
chcp 65001 >nul
echo.
echo  ╔══════════════════════════════════════════════╗
echo  ║   Mining Farm Manager — Build (Dashboard)    ║
echo  ╚══════════════════════════════════════════════╝
echo.

:: ── Sprawdź Python ───────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERR] Python nie znaleziony. Zainstaluj Python 3.11+
    pause & exit /b 1
)

:: ── Zainstaluj narzędzia budowania ───────────────
echo  [1/4] Instaluję narzędzia...
pip install pyarmor nuitka pyinstaller ordered-set zstandard --quiet

:: ── Katalogi ─────────────────────────────────────
set SRC=%~dp0
set BUILD=%SRC%build_tmp
set DIST=%SRC%dist

rmdir /s /q "%BUILD%" 2>nul
mkdir "%BUILD%"
mkdir "%DIST%" 2>nul

:: ── Skopiuj źródła do katalogu roboczego ─────────
xcopy /e /i /q "%SRC%*.py"        "%BUILD%\" >nul
xcopy /e /i /q "%SRC%ui\"         "%BUILD%\ui\" >nul
xcopy /e /i /q "%SRC%agent\"      "%BUILD%\agent\" >nul

:: ── WARSTWA 1: PyArmor — szyfrowanie bytecode ────
echo  [2/4] PyArmor — szyfrowanie źródeł...
cd /d "%BUILD%"
pyarmor gen --output pyarmor_dist --recursive .
if errorlevel 1 (
    echo  [ERR] PyArmor nieudany
    pause & exit /b 1
)

:: Zastąp źródła zaszyfrowanymi wersjami
xcopy /e /i /q "pyarmor_dist\" ".\" >nul
rmdir /s /q "pyarmor_dist" 2>nul

:: ── WARSTWA 2: Nuitka — kompilacja Python → C → EXE ──
echo  [3/4] Nuitka — kompilacja do natywnego kodu...
python -m nuitka ^
    --onefile ^
    --standalone ^
    --windows-disable-console ^
    --output-dir="%DIST%" ^
    --output-filename="MiningFarmManager.exe" ^
    --include-package=ui ^
    --include-package=PyQt6 ^
    --include-package=flask ^
    --include-package=psutil ^
    --include-package=requests ^
    --enable-plugin=pyqt6 ^
    --windows-icon-from-ico="%SRC%icon.ico" 2>nul ^
    --assume-yes-for-downloads ^
    main.py

if errorlevel 1 (
    echo  [WARN] Nuitka nieudany — próbuję PyInstaller jako fallback...
    pyinstaller ^
        --onefile ^
        --windowed ^
        --name "MiningFarmManager" ^
        --distpath "%DIST%" ^
        --workpath "%BUILD%\pyinst_work" ^
        --specpath "%BUILD%" ^
        --add-data "ui;ui" ^
        main.py
)

:: ── Sprzątanie ────────────────────────────────────
echo  [4/4] Czyszczę pliki tymczasowe...
cd /d "%SRC%"
rmdir /s /q "%BUILD%" 2>nul

echo.
echo  ✓ Gotowe!  Plik: %DIST%\MiningFarmManager.exe
echo.
pause
