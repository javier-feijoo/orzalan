param(
    [string]$Name = "orzalan"
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

pyinstaller `
    --noconfirm `
    --clean `
    --name $Name `
    --windowed `
    --onedir `
    --specpath . `
    --distpath dist `
    --workpath build `
    orzalan.spec

if (Test-Path "dist\\$Name\\assets") {
    Copy-Item -Recurse -Force "assets\\*" "dist\\$Name\\assets\\"
} else {
    New-Item -ItemType Directory -Path "dist\\$Name\\assets" | Out-Null
    Copy-Item -Recurse -Force "assets\\*" "dist\\$Name\\assets\\"
}

Write-Host "Build listo en dist\\$Name"
