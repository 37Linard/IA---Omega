@echo off
echo.
echo  ============================================================
echo   Agente IA Local -- porta unica: localhost:8000
echo  ============================================================
echo.

cd /d "%~dp0"

echo [1/2] Compilando frontend Next.js...
cd frontend
call npm run build
if errorlevel 1 (
    echo ERRO: Build do frontend falhou.
    pause
    exit /b 1
)
cd ..

echo.
echo [2/2] Iniciando servidor em localhost:8000 ...
timeout /t 1 /nobreak > nul
start "" http://localhost:8000

set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
C:\Users\User\AppData\Local\Python\pythoncore-3.14-64\python.exe -m uvicorn api:app --host 0.0.0.0 --port 8000 --reload

pause
