@echo off
REM ═══════════════════════════════════════════════════════════
REM  Olist BI Backend (FastAPI + Hive) — Arranque seguro
REM ═══════════════════════════════════════════════════════════

cd /d "%~dp0"

venv\Scripts\python.exe -c "print('venv OK')" >nul 2>&1
if %errorlevel%==0 (
    echo [OK] Usando venv Python 3.14
    set PYTHON=venv\Scripts\python.exe
) else (
    echo [INFO] venv no disponible, usando Python global 3.14
    set PYTHON=C:\Python314\python.exe
)

echo.
echo  Backend API: http://localhost:8000
echo  Docs:        http://localhost:8000/docs
echo  Presiona Ctrl+C para detener
echo.

%PYTHON% -m uvicorn backend.main:app --reload --port 8000
pause
