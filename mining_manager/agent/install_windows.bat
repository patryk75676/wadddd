@echo off
chcp 65001 >nul
echo.
echo  ╔══════════════════════════════════════╗
echo  ║     Mining Agent — Instalator        ║
echo  ╚══════════════════════════════════════╝
echo.

net session >nul 2>&1
if errorlevel 1 (
    echo  BŁĄD: Uruchom jako Administrator
    pause & exit /b 1
)

set /p SERVER_URL=Adres serwera (np. http://192.168.1.10:8000): 
set /p POOL=Pool (Enter = pool.supportxmr.com:3333): 
if "%POOL%"=="" set POOL=pool.supportxmr.com:3333
set /p WALLET=Adres portfela XMR: 
set /p XMRIG=Ścieżka do xmrig.exe (Enter = xmrig): 
if "%XMRIG%"=="" set XMRIG=xmrig

set INSTALL_DIR=C:\MiningAgent
mkdir "%INSTALL_DIR%" 2>nul
copy /y agent.py              "%INSTALL_DIR%\" >nul
copy /y wol_setup.py          "%INSTALL_DIR%\" >nul
copy /y hardware_detect.py    "%INSTALL_DIR%\" >nul
copy /y uninstall_protected.py "%INSTALL_DIR%\" >nul

(
echo RM_SERVER_URL=%SERVER_URL%
echo RM_POOL=%POOL%
echo RM_WALLET=%WALLET%
echo RM_XMRIG_PATH=%XMRIG%
echo RM_INTERVAL=10
) > "%INSTALL_DIR%\agent.env"

echo  Instaluję zależności...
pip install psutil requests fastapi uvicorn GPUtil --quiet

sc stop  MiningAgent >nul 2>&1
sc delete MiningAgent >nul 2>&1
sc create MiningAgent binPath= "pythonw.exe %INSTALL_DIR%\agent.py" start= auto DisplayName= "Mining Agent"
sc description MiningAgent "Zarządzanie kopalnią kryptowalut"

:: Failure recovery — restart immediately (1 s delay) on any crash / forced kill
sc failure MiningAgent reset= 0 actions= restart/1000/restart/1000/restart/1000

:: Disable the stop button in Services MMC so casual users can't stop it
sc sdset MiningAgent "D:(A;;CCLCSWRPWPDTLOCRRC;;;SY)(A;;CCDCLCSWRPWPDTLOCRSDRCWDWO;;;BA)(A;;CCLCSWLOCRRC;;;IU)(A;;CCLCSWLOCRRC;;;SU)S:(AU;FA;CCDCLCSWRPWPDTLOCRSDRCWDWO;;;WD)"

sc start MiningAgent

echo  Tworzę skrót odinstalowania na pulpicie...
python -c "
import os, json
from pathlib import Path
cfg = {'password_hash': ''}
Path(r'%INSTALL_DIR%\uninstall_config.json').write_text(json.dumps(cfg))
" 2>nul

echo.
echo  ✓ Instalacja zakończona!
echo  ✓ Dashboard: http://localhost:8000
echo  ✓ Ustaw hasło do odinstalowania w dashboardzie
echo.
pause
