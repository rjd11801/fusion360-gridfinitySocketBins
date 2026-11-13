<#
 SocketBinHoles installer (Windows). No administrator rights needed.
 Copies the SocketBinHoles folder next to this file into Fusion 360's per-user Scripts folder.
   -Target <folder>   install into <folder> instead of %APPDATA%\Autodesk\Autodesk Fusion 360\API\Scripts (for testing)
   -NoPause           do not wait for a key press at the end
#>
param([string]$Target = "", [switch]$NoPause)
$ErrorActionPreference = "Stop"
function Done($code) { if (-not $NoPause) { Write-Host ""; Read-Host "Press Enter to close" | Out-Null }; exit $code }
try {
    $src = Join-Path $PSScriptRoot "SocketBinHoles"
    if (-not (Test-Path (Join-Path $src "SocketBinHoles.py"))) {
        Write-Host "ERROR: cannot find the SocketBinHoles folder next to this installer ($src)." -ForegroundColor Red
        Write-Host "Unzip the whole package first, then run the installer from the unzipped folder."
        Done 1
    }
    if ($Target) { $scripts = $Target } else { $scripts = Join-Path $env:APPDATA "Autodesk\Autodesk Fusion 360\API\Scripts" }
    $dest = Join-Path $scripts "SocketBinHoles"
    $backups = Join-Path (Split-Path $scripts -Parent) "SocketBinHoles-backups"
    Write-Host "SocketBinHoles installer"
    Write-Host "  From: $src"
    Write-Host "  To:   $dest"
    New-Item -ItemType Directory -Force -Path $scripts | Out-Null

    $settings = $null
    if (Test-Path $dest) {
        $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
        $bak = Join-Path $backups ("SocketBinHoles-" + $stamp)
        New-Item -ItemType Directory -Force -Path $backups | Out-Null
        Copy-Item -Path $dest -Destination $bak -Recurse -Force
        Write-Host "  Existing install backed up to: $bak"
        $sf = Join-Path $dest "socketbin_settings.json"
        if (Test-Path $sf) { $settings = Get-Content -Raw -Path $sf }
        Remove-Item -Path $dest -Recurse -Force
    }
    Copy-Item -Path $src -Destination $dest -Recurse -Force
    Get-ChildItem -Path $dest -Recurse -File | Unblock-File -ErrorAction SilentlyContinue
    if ($settings) {
        [IO.File]::WriteAllText((Join-Path $dest "socketbin_settings.json"), $settings, (New-Object Text.UTF8Encoding $false))
        Write-Host "  Your remembered settings were kept."
    }
    Write-Host ""
    Write-Host "Installed SocketBinHoles. In Fusion 360 press Shift+S, open the Scripts tab, pick SocketBinHoles and click Run." -ForegroundColor Green
    Write-Host "If Fusion was already open, close and reopen the Scripts and Add-Ins window first."
    Done 0
} catch {
    Write-Host "ERROR: $($_.Exception.Message)" -ForegroundColor Red
    Done 1
}
