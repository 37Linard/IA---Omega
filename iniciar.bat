@echo off
cd /d "C:\Users\User\Desktop\MEU\IA"
echo Iniciando Agente IA Local...
echo.
for /f "tokens=2 delims=:" %%i in ('ipconfig ^| findstr /i "IPv4" ^| findstr /v "127.0.0.1"') do (
    set IP=%%i
    goto :found
)
:found
set IP=%IP: =%
echo Acesse no PC:      http://localhost:8000
echo Acesse no celular: http://%IP%:8000
echo.
C:\Users\User\AppData\Local\Python\pythoncore-3.14-64\python.exe -m uvicorn api:app --host 0.0.0.0 --port 8000
pause
