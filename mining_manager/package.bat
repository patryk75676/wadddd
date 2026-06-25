@echo off
chcp 65001 >nul
echo.
echo  ╔══════════════════════════════════════════════════╗
echo  ║   Mining Farm Manager — Pakowanie wydania        ║
echo  ╚══════════════════════════════════════════════════╝
echo.
echo  Tworzy folder release\ z dwoma wersjami:
echo    source\    — kod źródłowy (Python, do developmentu)
echo    compiled\  — skompilowany + zaszyfrowany (do produkcji)
echo.

set ROOT=%~dp0
set RELEASE=%ROOT%release
set SRC_OUT=%RELEASE%\source
set BLD_OUT=%RELEASE%\compiled
set BUILD_TMP=%ROOT%build_tmp

:: ── Sprzątanie ────────────────────────────────────────────────
rmdir /s /q "%RELEASE%"   2>nul
rmdir /s /q "%BUILD_TMP%" 2>nul
mkdir "%SRC_OUT%\dashboard"
mkdir "%SRC_OUT%\agent"
mkdir "%BLD_OUT%\dashboard"
mkdir "%BLD_OUT%\agent"
mkdir "%BUILD_TMP%"

:: ════════════════════════════════════════════════════════════════
:: WERSJA ŹRÓDŁOWA (source)
:: ════════════════════════════════════════════════════════════════
echo  [1/6] Kopiuję kod źródłowy dashboardu...
copy /y "%ROOT%main.py"         "%SRC_OUT%\dashboard\" >nul
copy /y "%ROOT%state.py"        "%SRC_OUT%\dashboard\" >nul
copy /y "%ROOT%server.py"       "%SRC_OUT%\dashboard\" >nul
copy /y "%ROOT%requirements.txt" "%SRC_OUT%\dashboard\" >nul
xcopy /e /i /q "%ROOT%ui\"     "%SRC_OUT%\dashboard\ui\" >nul

echo  [2/6] Kopiuję kod źródłowy agenta...
copy /y "%ROOT%agent\agent.py"           "%SRC_OUT%\agent\" >nul
copy /y "%ROOT%agent\hardware_detect.py" "%SRC_OUT%\agent\" >nul
copy /y "%ROOT%agent\wol_setup.py"       "%SRC_OUT%\agent\" >nul
copy /y "%ROOT%agent\install_windows.bat" "%SRC_OUT%\agent\" >nul
copy /y "%ROOT%agent\install_linux.sh"   "%SRC_OUT%\agent\" >nul

:: Instrukcja uruchomienia ze źródeł
(
echo # Uruchomienie ze źródeł
echo.
echo ## Dashboard
echo ```
echo pip install PyQt6 Flask psutil requests
echo cd source\dashboard
echo python main.py
echo ```
echo.
echo ## Agent (na maszynach kopalni)
echo ```
echo pip install psutil requests
echo cd source\agent
echo :: Edytuj agent.env i wpisz dane serwera, poolu i portfela
echo :: Następnie uruchom instalator:
echo install_windows.bat
echo ```
) > "%SRC_OUT%\INSTALACJA_ZRODLA.md"

:: ════════════════════════════════════════════════════════════════
:: WERSJA SKOMPILOWANA (compiled)
:: ════════════════════════════════════════════════════════════════
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERR] Python nie znaleziony — nie można skompilować wersji compiled
    echo  Wersja source jest gotowa w: %SRC_OUT%
    pause & exit /b 1
)

echo  [3/6] Instaluję narzędzia (PyArmor, Nuitka, PyInstaller)...
pip install pyarmor nuitka pyinstaller PyQt6 Flask psutil requests ordered-set zstandard --quiet

:: ── Budowanie dashboardu ─────────────────────────────────────
echo  [4/6] Budowanie dashboardu (PyArmor + Nuitka)...
mkdir "%BUILD_TMP%\dashboard"
copy /y "%ROOT%*.py"       "%BUILD_TMP%\dashboard\" >nul
xcopy /e /i /q "%ROOT%ui\" "%BUILD_TMP%\dashboard\ui\" >nul

cd /d "%BUILD_TMP%\dashboard"

:: Warstwa 1 — PyArmor
pyarmor gen --output pa_dist --recursive . >nul 2>&1
if not errorlevel 1 (
    xcopy /e /i /q "pa_dist\" ".\" >nul
    rmdir /s /q "pa_dist" 2>nul
)

:: Warstwa 2 — Nuitka → EXE
python -m nuitka --onefile --standalone --windows-disable-console ^
    --output-dir="%BLD_OUT%\dashboard" ^
    --output-filename="MiningFarmManager.exe" ^
    --include-package=ui --include-package=PyQt6 ^
    --include-package=flask --include-package=psutil ^
    --include-package=requests --enable-plugin=pyqt6 ^
    --assume-yes-for-downloads main.py >nul 2>&1
if errorlevel 1 (
    echo  [WARN] Nuitka nieudana — używam PyInstaller dla dashboardu...
    cd /d "%BUILD_TMP%\dashboard"
    pyinstaller --onefile --windowed --name "MiningFarmManager" ^
        --distpath "%BLD_OUT%\dashboard" ^
        --workpath "%BUILD_TMP%\pyinst_d" ^
        --specpath "%BUILD_TMP%" ^
        --add-data "ui;ui" main.py >nul 2>&1
)

:: ── Budowanie agenta ─────────────────────────────────────────
echo  [5/6] Budowanie agenta (PyArmor + Nuitka)...
mkdir "%BUILD_TMP%\agent"
copy /y "%ROOT%agent\agent.py"            "%BUILD_TMP%\agent\" >nul
copy /y "%ROOT%agent\hardware_detect.py"  "%BUILD_TMP%\agent\" >nul
copy /y "%ROOT%agent\wol_setup.py"        "%BUILD_TMP%\agent\" >nul

cd /d "%BUILD_TMP%\agent"

:: Warstwa 1 — PyArmor
pyarmor gen --output pa_dist agent.py hardware_detect.py wol_setup.py >nul 2>&1
if not errorlevel 1 (
    xcopy /e /i /q "pa_dist\" ".\" >nul
    rmdir /s /q "pa_dist" 2>nul
)

:: Warstwa 2 — Nuitka → EXE
python -m nuitka --onefile --standalone ^
    --output-dir="%BLD_OUT%\agent" ^
    --output-filename="agent.exe" ^
    --include-package=psutil --include-package=requests ^
    --assume-yes-for-downloads agent.py >nul 2>&1
if errorlevel 1 (
    echo  [WARN] Nuitka nieudana — używam PyInstaller dla agenta...
    pyinstaller --onefile --name "agent" ^
        --distpath "%BLD_OUT%\agent" ^
        --workpath "%BUILD_TMP%\pyinst_a" ^
        --specpath "%BUILD_TMP%" agent.py >nul 2>&1
)

:: Skopiuj instalatory do compiled\agent
copy /y "%ROOT%agent\install_windows.bat" "%BLD_OUT%\agent\" >nul
copy /y "%ROOT%agent\install_linux.sh"   "%BLD_OUT%\agent\" >nul

:: Instrukcja dla compiled
(
echo # Instalacja — wersja skompilowana
echo.
echo ## Dashboard (Twój komputer)
echo Uruchom: `compiled\dashboard\MiningFarmManager.exe`
echo Nie wymaga instalacji Pythona.
echo.
echo ## Agent (maszyny kopalni^)
echo 1. Skopiuj folder `compiled\agent\` na maszynę kopalni
echo 2. Uruchom `install_windows.bat` jako Administrator
echo Agent zostanie zainstalowany jako usługa systemowa.
echo Nie wymaga instalacji Pythona na maszynie kopalni.
) > "%BLD_OUT%\INSTALACJA_COMPILED.md"

:: ── Sprzątanie ────────────────────────────────────────────────
echo  [6/6] Czyszczę pliki tymczasowe...
cd /d "%ROOT%"
rmdir /s /q "%BUILD_TMP%" 2>nul

:: ── Podsumowanie ──────────────────────────────────────────────
echo.
echo  ════════════════════════════════════════════════════
echo   Wydanie gotowe w: %RELEASE%
echo  ════════════════════════════════════════════════════
echo.
echo   release\
echo   ├── source\
echo   │   ├── dashboard\    ← kod źródłowy dashboardu (Python)
echo   │   ├── agent\        ← kod źródłowy agenta (Python)
echo   │   └── INSTALACJA_ZRODLA.md
echo   └── compiled\
echo       ├── dashboard\    ← MiningFarmManager.exe (zaszyfrowany)
echo       ├── agent\        ← agent.exe + install_windows.bat
echo       └── INSTALACJA_COMPILED.md
echo.
pause
