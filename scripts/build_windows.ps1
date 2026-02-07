param(
    [string]$Name = "orzalan"
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$buildDir = Join-Path $root "build"
if (Test-Path $buildDir) {
    attrib -R "$buildDir" /S /D | Out-Null
    cmd /c rmdir /s /q "$buildDir"
}

$distDir = Join-Path $root "dist"
if (Test-Path $distDir) {
    attrib -R "$distDir" /S /D | Out-Null
    cmd /c rmdir /s /q "$distDir"
}

$venvPy = Join-Path $root ".venv\\Scripts\\pyinstaller.exe"
$pyiCmd = if (Test-Path $venvPy) { $venvPy } else { "pyinstaller" }

& $pyiCmd `
    --noconfirm `
    --clean `
    orzalan.spec

if (Test-Path "dist\\$Name\\assets") {
    Copy-Item -Recurse -Force "assets\\*" "dist\\$Name\\assets\\"
} else {
    New-Item -ItemType Directory -Path "dist\\$Name\\assets" | Out-Null
    Copy-Item -Recurse -Force "assets\\*" "dist\\$Name\\assets\\"
}

$zipPath = Join-Path $root "dist\\$Name.zip"
if (Test-Path $zipPath) {
    Remove-Item -Force $zipPath
}
Compress-Archive -Path "dist\\$Name\\*" -DestinationPath $zipPath -Force

Write-Host "Build listo en dist\\$Name"
Write-Host "Zip listo en dist\\$Name.zip"
