<#
 SocketBinHoles uninstaller (Windows). Removes the SocketBinHoles folder from Fusion 360's per-user Scripts folder.
 Your designs and exported files are not touched.
   -Target <folder>   Scripts folder to remove from (default: %APPDATA%\Autodesk\Autodesk Fusion 360\API\Scripts)
   -Yes               do not ask for confirmation
   -NoPause           do not wait for a key press at the end
#>
param([string]$Target = "", [switch]$Yes, [switch]$NoPause)
$ErrorActionPreference = "Stop"
function Done($code) { if (-not $NoPause) { Write-Host ""; Read-Host "Press Enter to close" | Out-Null }; exit $code }
try {
    if ($Target) { $scripts = $Target } else { $scripts = Join-Path $env:APPDATA "Autodesk\Autodesk Fusion 360\API\Scripts" }
    $dest = Join-Path $scripts "SocketBinHoles"
    if (-not (Test-Path $dest)) { Write-Host "SocketBinHoles is not installed at $dest. Nothing to do."; Done 0 }
    if (-not (Test-Path (Join-Path $dest "SocketBinHoles.manifest"))) {
        Write-Host "The folder $dest does not look like SocketBinHoles (no SocketBinHoles.manifest). Not removing it." -ForegroundColor Red
        Done 1
    }
    if (-not $Yes) {
        $a = Read-Host "Remove $dest ? (y/N)"
        if ($a -notmatch '^(y|yes)$') { Write-Host "Cancelled."; Done 0 }
    }
    Remove-Item -Path $dest -Recurse -Force
    Write-Host "SocketBinHoles removed. Backups of earlier installs (if any) are in $(Join-Path (Split-Path $scripts -Parent) 'SocketBinHoles-backups')." -ForegroundColor Green
    Done 0
} catch {
    Write-Host "ERROR: $($_.Exception.Message)" -ForegroundColor Red
    Done 1
}
