$ErrorActionPreference = "Stop"

$source = "C:\Users\User\Desktop\MEU\IA"
$dest   = "C:\Users\User\OneDrive\Backups_IA"
New-Item -ItemType Directory -Force -Path $dest | Out-Null

$stamp   = Get-Date -Format "yyyy-MM-dd_HHmm"
$zipPath = Join-Path $dest "IA_backup_$stamp.zip"
$staging = Join-Path $env:TEMP "ia_backup_staging"

if (Test-Path $staging) { Remove-Item -Recurse -Force $staging }
New-Item -ItemType Directory -Force -Path $staging | Out-Null

Copy-Item (Join-Path $source "workspace") -Destination (Join-Path $staging "workspace") -Recurse
Copy-Item (Join-Path $source "agent_memory.json") -Destination $staging

Compress-Archive -Path (Join-Path $staging "*") -DestinationPath $zipPath -CompressionLevel Optimal
Remove-Item -Recurse -Force $staging

# Retenção: apaga backups com mais de 90 dias
Get-ChildItem $dest -Filter "IA_backup_*.zip" |
    Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-90) } |
    Remove-Item -Force

Write-Output "Backup criado: $zipPath"
