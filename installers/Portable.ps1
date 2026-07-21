# ==========================================================
# FitFetch Portable Installer
# ==========================================================
#
# Repository : https://github.com/BrainlessDip/FitFetch
# Project    : FitFetch
#
# Description:
#   Downloads the latest portable release from GitHub,
#   automatically detects the ZIP asset, installs it into
#   a versioned folder, removes older versions, and launches
#   the latest FitFetch build.
#
# Features:
#   - Automatic latest version detection
#   - GitHub Release API integration
#   - ZIP asset auto discovery
#   - Version-based installation
#   - Automatic old version cleanup
#   - Portable installation (no registry changes)
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File Install-FitFetch.ps1
#
# ==========================================================
$Repo = "BrainlessDip/FitFetch"
$ApiUrl = "https://api.github.com/repos/$Repo/releases/latest"

$AppName = "FitFetch"
$RootDir = Join-Path $env:LOCALAPPDATA $AppName

$Headers = @{
    "User-Agent" = "$AppName Installer"
}

function Write-Step {
    param(
        [string]$Message
    )

    Write-Host ""
    Write-Host "[*] $Message" -ForegroundColor Cyan
}

function Write-Success {
    param(
        [string]$Message
    )

    Write-Host "[+] $Message" -ForegroundColor Green
}

function Write-ErrorMessage {
    param(
        [string]$Message
    )

    Write-Host "[!] $Message" -ForegroundColor Red
}


Clear-Host

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "       FitFetch Portable Installer" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan


# ----------------------------------------------------------
# Fetch latest release information
# ----------------------------------------------------------

Write-Step "Checking latest GitHub release..."

try {
    $Release = Invoke-RestMethod `
        -Uri $ApiUrl `
        -Headers $Headers `
        -ErrorAction Stop
}
catch {
    Write-ErrorMessage "Unable to fetch release information."
    exit 1
}


$Version = $Release.tag_name.TrimStart("v")


# ----------------------------------------------------------
# Find ZIP asset automatically
# ----------------------------------------------------------

Write-Step "Searching release assets..."

$ZipAsset = $Release.assets |
    Where-Object {
        $_.name -match "\.zip$"
    } |
    Select-Object -First 1


if (-not $ZipAsset) {
    Write-ErrorMessage "No ZIP file found in the latest release."
    exit 1
}


$DownloadUrl = $ZipAsset.browser_download_url


Write-Host ""
Write-Host "Version : v$Version" -ForegroundColor Yellow
Write-Host "Asset   : $($ZipAsset.name)"
Write-Host "Date    : $($Release.published_at)"
Write-Host ""


# ----------------------------------------------------------
# Prepare install paths
# ----------------------------------------------------------

$InstallDir = Join-Path $RootDir "v$Version"
$ZipFile = Join-Path $env:TEMP "$AppName-$Version.zip"


if (!(Test-Path $RootDir)) {
    New-Item `
        -ItemType Directory `
        -Path $RootDir `
        -Force | Out-Null
}


# ----------------------------------------------------------
# Install latest version
# ----------------------------------------------------------

if (Test-Path $InstallDir) {

    Write-Host "FitFetch v$Version is already installed." `
        -ForegroundColor Yellow

}
else {

    Write-Step "Downloading latest FitFetch..."

    try {
        Invoke-WebRequest `
            -Uri $DownloadUrl `
            -OutFile $ZipFile `
            -Headers $Headers `
            -ErrorAction Stop
    }
    catch {
        Write-ErrorMessage "Download failed."
        exit 1
    }


    Write-Step "Extracting files..."

    New-Item `
        -ItemType Directory `
        -Path $InstallDir `
        -Force | Out-Null


    try {
        Expand-Archive `
            -Path $ZipFile `
            -DestinationPath $InstallDir `
            -Force
    }
    catch {
        Write-ErrorMessage "Extraction failed."
        exit 1
    }


    Remove-Item `
        $ZipFile `
        -Force `
        -ErrorAction SilentlyContinue


    Write-Success "FitFetch v$Version installed."


    # ------------------------------------------------------
    # Remove old versions
    # ------------------------------------------------------

    Write-Step "Removing old versions..."


    Get-ChildItem `
        -Path $RootDir `
        -Directory |
    Where-Object {
        $_.Name -like "v*" -and
        $_.FullName -ne $InstallDir
    } |
    ForEach-Object {

        Write-Host "Removing $($_.Name)..."

        Remove-Item `
            $_.FullName `
            -Recurse `
            -Force
    }


    Write-Success "Cleanup completed."
}


# ----------------------------------------------------------
# Launch application
# ----------------------------------------------------------

$Exe = Join-Path $InstallDir "FitFetch.exe"


if (Test-Path $Exe) {

    Write-Step "Launching FitFetch..."

    Start-Process $Exe

    Write-Success "FitFetch started."

}
else {

    Write-ErrorMessage "FitFetch.exe not found."
    exit 1

}


Write-Host ""
Write-Host "Installation finished successfully." `
    -ForegroundColor Green
Write-Host ""