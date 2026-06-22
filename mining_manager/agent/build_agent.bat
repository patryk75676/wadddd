@echo off
chcp 65001 >nul
echo.
echo  ╔══════════════════════════════════════════════╗
echo  ║   Mining Farm Manager — Build (Agent)        ║
echo  ╚══════════════════════════════════════════════╝
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERR] Python nie znaleziony
    pause & exit /b 1
)

set SRC=%~dp0
set BUILD=%SRC%build_tmp
set DIST=%SRC%dist

rmdir /s /q "%BUILD%" 2>nul
mkdir "%BUILD%"
mkdir "%DIST%" 2>nul

echo  [1/4] Instaluję narzędzia...
pip install pyarmor nuitka pyinstaller psutil requests ordered-set zstandard --quiet

echo  [2/4] Kopiuję źródła agenta...
copy /y "%SRC%agent.py"          "%BUILD%\" >nul
copy /y "%SRC%hardware_detect.py" "%BUILD%\" >nul
copy /y "%SRC%wol_setup.py"       "%BUILD%\" >nul

echo  [3/4] PyArmor — szyfrowanie bytecode...
cd /d "%BUILD%"
pyarmor gen --output pyarmor_dist agent.py hardware_detect.py wol_setup.py
if errorlevel 1 (
    echo  [ERR] PyArmor nieudany
    pause & exit /b 1
)
xcopy /e /i /q "pyarmor_dist\" ".\" >nul
rmdir /s /q "pyarmor_dist" 2>nul

echo  [4/4] Nuitka — kompilacja Python → natywne EXE...
python -m nuitka ^
    --onefile ^
    --standalone ^
    --output-dir="%DIST%" ^
    --output-filename="agent.exe" ^
    --include-package=psutil ^
    --include-package=requests ^
    --assume-yes-for-downloads ^
    agent.py

if errorlevel 1 (
    echo  [WARN] Nuitka nieudana — próbuję PyInstaller...
    pyinstaller ^
        --onefile ^
        --console ^
        --name "agent" ^
        --distpath "%DIST%" ^
        --workpath "%BUILD%\pyinst_work" ^
        --specpath "%BUILD%" ^
        agent.py
)

cd /d "%SRC%"
rmdir /s /q "%BUILD%" 2>nul

:: Skopiuj instalatory obok gotowego exe
copy /y "%SRC%install_windows.bat" "%DIST%\" >nul

echo.
echo  ✓ Gotowe!
echo  ✓ Agent EXE:    %DIST%\agent.exe
echo  ✓ Instalator:   %DIST%\install_windows.bat
echo.
echo  Skopiuj folder %DIST%\ na maszynę kopalni i uruchom install_windows.bat
echo.
pause
