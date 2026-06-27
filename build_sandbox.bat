@echo off
echo Buildando imagem ia-sandbox:latest...
docker build -f sandbox.Dockerfile -t ia-sandbox:latest .
if %ERRORLEVEL% == 0 (
    echo.
    echo [OK] ia-sandbox:latest buildada com sucesso.
    echo Bibliotecas disponiveis: numpy, pandas, matplotlib, scipy, pillow, requests
) else (
    echo.
    echo [ERRO] Build falhou. Verifique se Docker Desktop esta rodando.
)
pause
