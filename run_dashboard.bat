@echo off
REM ═══════════════════════════════════════════════════════════
REM  Olist BI Dashboard — Arranque seguro
REM  Usa Python 3.14 (global) o venv si está disponible
REM ═══════════════════════════════════════════════════════════

cd /d "%~dp0"

REM Verificar si el venv de Python 3.14 funciona
venv\Scripts\python.exe -c "print('venv OK')" >nul 2>&1
if %errorlevel%==0 (
    echo [OK] Usando venv Python 3.14
    set PYTHON=venv\Scripts\python.exe
    set PIP=venv\Scripts\pip.exe
) else (
    echo [INFO] venv no disponible, usando Python global 3.14
    set PYTHON=C:\Python314\python.exe
    set PIP=C:\Python314\Scripts\pip.exe
)

echo.
echo  Abre en el navegador: http://localhost:8050
echo  API Docs:  http://localhost:8000/docs
echo  Presiona Ctrl+C para detener
echo.

%PYTHON% dashboard/app.py
pause
