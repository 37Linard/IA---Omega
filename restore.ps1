<#
Restaura workspace/ + agent_memory.json a partir de um zip do backup_workspace.ps1.
Destrutivo por natureza (sobrescreve os dados reais) - por padrao:
  1. tira um snapshot de seguranca do estado ATUAL antes de mexer em qualquer
     coisa (reusa backup_workspace.ps1 - se o restore sair errado, da pra
     desfazer rodando restore.ps1 de novo apontando pro snapshot);
  2. pede confirmacao explicita (y) antes de sobrescrever.

Uso:
    .\restore.ps1                          # restaura o backup mais recente em Backups_IA
    .\restore.ps1 -ZipPath "C:\...\IA_backup_2026-07-26_2209.zip"
    .\restore.ps1 -Force                   # pula a confirmacao (scripts/automacao)
    .\restore.ps1 -NoSafetyBackup          # pula o snapshot de seguranca (nao recomendado)
#>
param(
    [string]$ZipPath,
    [switch]$Force,
    [switch]$NoSafetyBackup
)

$ErrorActionPreference = "Stop"

$source        = "C:\Users\User\Desktop\MEU\IA"
$workspaceReal = "C:\Users\User\Desktop\MEU\ia-workspace-data"   # alvo real da junction workspace/
$backupsDir    = "C:\Users\User\OneDrive\Backups_IA"

# ---------------------------------------------------------------------------
# 1. Resolve qual zip restaurar
# ---------------------------------------------------------------------------
if (-not $ZipPath) {
    $latest = Get-ChildItem $backupsDir -Filter "IA_backup_*.zip" |
        Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if (-not $latest) {
        Write-Error "Nenhum backup encontrado em $backupsDir - rode backup_workspace.ps1 primeiro ou passe -ZipPath."
        exit 1
    }
    $ZipPath = $latest.FullName
}
if (-not (Test-Path $ZipPath)) {
    Write-Error "Zip nao encontrado: $ZipPath"
    exit 1
}
Write-Output "Zip escolhido: $ZipPath"

# ---------------------------------------------------------------------------
# 2. Extrai pra staging e valida ANTES de tocar em qualquer arquivo real -
#    zip incompleto/corrompido aborta aqui, nao a meio caminho de sobrescrever.
# ---------------------------------------------------------------------------
$staging = Join-Path $env:TEMP "ia_restore_staging"
if (Test-Path $staging) { Remove-Item -Recurse -Force $staging }
New-Item -ItemType Directory -Force -Path $staging | Out-Null

Expand-Archive -Path $ZipPath -DestinationPath $staging

$stagedMemory    = Join-Path $staging "agent_memory.json"
$stagedWorkspace = Join-Path $staging "workspace"
if (-not (Test-Path $stagedMemory)) {
    Write-Error "Zip invalido - agent_memory.json nao encontrado dentro do backup. Nada foi restaurado."
    Remove-Item -Recurse -Force $staging
    exit 1
}
if (-not (Test-Path $stagedWorkspace)) {
    Write-Error "Zip invalido - workspace/ nao encontrado dentro do backup. Nada foi restaurado."
    Remove-Item -Recurse -Force $staging
    exit 1
}
# ConvertFrom-Json do PowerShell 5.1 monta dicionario case-INSENSITIVE -
# agent_memory.json real tem chaves que so diferem em maiusculas (ex:
# "Imagem gerada" vs "imagem gerada", JSON valido, cada uma um campo
# distinto) e o cmdlet rejeita isso como "chave duplicada", falso positivo.
# Valida com o Python real do projeto (mesmo parser que a aplicacao usa).
$pythonExe = "C:\Users\User\AppData\Local\Python\pythoncore-3.14-64\python.exe"
& $pythonExe -c "import json,sys; json.load(open(sys.argv[1], encoding='utf-8'))" $stagedMemory
if ($LASTEXITCODE -ne 0) {
    Write-Error "agent_memory.json dentro do zip nao e JSON valido. Nada foi restaurado."
    Remove-Item -Recurse -Force $staging
    exit 1
}
Write-Output "Zip validado - agent_memory.json e JSON valido, workspace/ presente."

# ---------------------------------------------------------------------------
# 3. Confirmacao - restore sobrescreve dados reais
# ---------------------------------------------------------------------------
if (-not $Force) {
    $resp = Read-Host "Isso vai SOBRESCREVER agent_memory.json e workspace/ atuais com o conteudo do zip. Continuar? (y/N)"
    if ($resp -ne "y" -and $resp -ne "Y") {
        Write-Output "Cancelado - nada foi alterado."
        Remove-Item -Recurse -Force $staging
        exit 0
    }
}

# ---------------------------------------------------------------------------
# 4. Snapshot de seguranca do estado ATUAL antes de sobrescrever (reusa o
#    proprio backup_workspace.ps1 - mesmo mecanismo, ja testado)
# ---------------------------------------------------------------------------
if (-not $NoSafetyBackup) {
    Write-Output "Tirando snapshot de seguranca do estado atual antes de restaurar..."
    & (Join-Path $source "backup_workspace.ps1")
}

# ---------------------------------------------------------------------------
# 5. Restaura de verdade
#    - agent_memory.json: copia direta
#    - workspace/: robocopy /MIR pro alvo REAL da junction (nao pra
#      workspace/ do repo - escrever direto na junction funciona, mas mirar
#      o alvo real evita qualquer ambiguidade de reparse point)
# ---------------------------------------------------------------------------
Copy-Item $stagedMemory -Destination (Join-Path $source "agent_memory.json") -Force

robocopy $stagedWorkspace $workspaceReal /MIR /NFL /NDL /NJH /NJS | Out-Null
if ($LASTEXITCODE -ge 8) {
    Write-Error "robocopy falhou (exit code $LASTEXITCODE) - workspace/ pode estar parcialmente restaurado. Confira o snapshot de seguranca."
    Remove-Item -Recurse -Force $staging
    exit 1
}

Remove-Item -Recurse -Force $staging
Write-Output "Restore concluido a partir de: $ZipPath"
