@echo off
echo Baixando CPython 3.12.0 compilado pra WASI (sandbox WASM, ~26MB)...
if not exist sandbox_wasm mkdir sandbox_wasm
curl -sL -o sandbox_wasm\python-3.12.0.wasm "https://github.com/vmware-labs/webassembly-language-runtimes/releases/download/python/3.12.0%%2B20231211-040d5a6/python-3.12.0.wasm"
if %ERRORLEVEL% == 0 (
    echo.
    echo [OK] sandbox_wasm\python-3.12.0.wasm baixado.
    echo run_python vai preferir WASM ao Docker automaticamente a partir de agora.
    echo Requer: pip install wasmtime
) else (
    echo.
    echo [ERRO] Download falhou. Verifique sua conexao com github.com.
)
pause
