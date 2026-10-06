@echo off
setlocal EnableExtensions
chcp 65001 >nul
cd /d "%~dp0"
title DiputadoDetector - Instalacion
set "ROOT=%~dp0"
set "UV=%ROOT%.tools\uv\uv.exe"
set "PY=%ROOT%.tools\python312\python.exe"
set "VENV_PY=%ROOT%.venv\Scripts\python.exe"
set "UV_CACHE_DIR=%ROOT%.tools\uv-cache"
set "UV_PYTHON_DOWNLOADS=never"
set "UV_LINK_MODE=hardlink"
set "PYTHONUTF8=1"

echo.
echo  ==============================================================
echo    DiputadoDetector - instalacion en un clic
echo    Todo se instala dentro de esta carpeta. No toca tu sistema.
echo  ==============================================================
echo.

echo [1/6] Preparando el gestor de paquetes uv...
if not exist "%UV%" (
    powershell -NoProfile -ExecutionPolicy Bypass -Command "$env:UV_INSTALL_DIR='%ROOT%.tools\uv'; $env:UV_NO_MODIFY_PATH='1'; irm https://astral.sh/uv/install.ps1 | iex"
)
if not exist "%UV%" goto :error_uv

echo [2/6] Preparando Python 3.12 oficial (firmado por python.org)...
if not exist "%PY%" (
    powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT%scripts\get_python.ps1" -Target "%ROOT%.tools"
)
if not exist "%PY%" goto :error_py

echo [3/6] Instalando librerias (la primera vez tarda 5-10 minutos)...
"%UV%" sync --frozen --python "%PY%"
if errorlevel 1 goto :error_deps

echo [4/6] Comprobando tu equipo...
"%VENV_PY%" scripts\check_system.py
if errorlevel 1 goto :error_check

echo [5/6] Descargando modelos de IA (unos 25 GB la primera vez)...
set "LIGHT="
where nvidia-smi >nul 2>nul || set "LIGHT=--light"
"%VENV_PY%" scripts\download_models.py %LIGHT%
if errorlevel 1 goto :error_models

echo [6/6] Preparando datos de la demo...
"%VENV_PY%" scripts\build_index.py
if errorlevel 1 goto :error_index

echo.
echo  Instalacion completada. Arrancando la aplicacion...
call "%ROOT%ARRANCAR.bat"
exit /b 0

:error_uv
echo [FALLO] No he podido instalar uv. Comprueba tu conexion a internet.
goto :end
:error_py
echo [FALLO] No he podido descargar Python. Comprueba tu conexion a internet.
goto :end
:error_deps
echo [FALLO] La instalacion de librerias ha fallado. Vuelve a ejecutar este archivo.
goto :end
:error_check
echo [FALLO] Tu equipo no cumple algun requisito (mira los mensajes de arriba).
goto :end
:error_models
echo [FALLO] Faltan modelos por descargar. Vuelve a ejecutar este archivo: retomara donde lo dejo.
goto :end
:error_index
echo [FALLO] No he podido preparar los datos de la demo.
:end
echo.
pause
exit /b 1
