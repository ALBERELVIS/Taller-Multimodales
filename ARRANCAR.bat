@echo off
setlocal EnableExtensions
chcp 65001 >nul
cd /d "%~dp0"
title DiputadoDetector
set "VENV_PY=%~dp0.venv\Scripts\python.exe"
set "PYTHONUTF8=1"

if not exist "%VENV_PY%" (
    echo Aun no esta instalado. Lanzo el instalador...
    call "%~dp0INSTALAR_Y_ARRANCAR.bat"
    exit /b
)
if exist "%~dp0models\.complete" set "DD_OFFLINE=1"

echo.
echo  DiputadoDetector se esta iniciando. Se abrira tu navegador en unos segundos.
echo  Para cerrar la aplicacion, cierra esta ventana.
echo.
"%VENV_PY%" -m app.main
if errorlevel 1 (
    echo.
    echo [FALLO] La aplicacion se ha cerrado con un error. Revisa los mensajes de arriba.
    pause
)
