# ==========================================================
# FitFetch Setup Installer Bootstrapper
# ==========================================================
#
# Repository : https://github.com/BrainlessDip/FitFetch
# Project    : FitFetch
#
# Description:
#   Downloads the latest FitFetch setup installer from GitHub,
#   automatically detects the EXE installer asset, and runs
#   the installation wizard.
#
# Features:
#   - Automatic latest version detection
#   - GitHub Release API integration
#   - EXE installer auto discovery
#   - Download progress animation
#   - Runs official setup wizard
#   - No bundled outdated installer
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File Install-FitFetch-Setup.ps1
#   irm "https://fitfetch.pages.dev/installers/Setup.ps1" | iex
#
# ==========================================================

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

Clear-Host

[Console]::CursorVisible = $false

Register-EngineEvent PowerShell.Exiting -Action {
    [Console]::CursorVisible = $true
} | Out-Null


# ----------------------------------------------------------
# Configuration
# ----------------------------------------------------------

$Repo = "BrainlessDip/FitFetch"
$ApiUrl = "https://api.github.com/repos/$Repo/releases/latest"
$AppName = "FitFetch"

$Headers = @{
    "User-Agent" = "$AppName Setup Installer"
}


# ----------------------------------------------------------
# Helper functions
# ----------------------------------------------------------

function Write-Banner {
    Write-Host ""
    Write-Host "  ==========================================" -ForegroundColor Cyan
    Write-Host "  " -NoNewline
    Write-Host "       FitFetch Setup Installer" -ForegroundColor White
    Write-Host "  ==========================================" -ForegroundColor Cyan
    Write-Host ""
}

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host "  [*] $Message" -ForegroundColor Cyan
}

function Write-Success {
    param([string]$Message)
    Write-Host "  [+] $Message" -ForegroundColor Green
}

function Write-WarningMessage {
    param([string]$Message)
    Write-Host "  [!] $Message" -ForegroundColor Yellow
}

function Write-ErrorMessage {
    param([string]$Message)
    Write-Host "  [!] $Message" -ForegroundColor Red
}

function Write-Info {
    param([string]$Label, [string]$Value)
    Write-Host "  " -NoNewline
    Write-Host "$Label : " -NoNewline -ForegroundColor DarkGray
    Write-Host $Value -ForegroundColor White
}

function Format-FileSize {
    param([long]$Bytes)

    if ($Bytes -ge 1GB) {
        return "{0:N1} GB" -f ($Bytes / 1GB)
    }
    elseif ($Bytes -ge 1MB) {
        return "{0:N1} MB" -f ($Bytes / 1MB)
    }
    elseif ($Bytes -ge 1KB) {
        return "{0:N1} KB" -f ($Bytes / 1KB)
    }
    else {
        return "$Bytes bytes"
    }
}

function Exit-Installer {
    param([int]$Code = 0)

    [Console]::CursorVisible = $true

    Write-Host ""
    Write-Host "  Press Enter to close..." -ForegroundColor DarkGray
    Read-Host | Out-Null
    break
}

function Cleanup {
    param([string]$FilePath)

    if ($FilePath -and (Test-Path $FilePath)) {
        try {
            Remove-Item $FilePath -Force -ErrorAction Stop
        }
        catch {
            try {
                $job = Start-Job -ScriptBlock {
                    param($Path)
                    Start-Sleep -Seconds 2
                    Remove-Item $Path -Force -ErrorAction SilentlyContinue
                } -ArgumentList $FilePath
                Register-ObjectEvent $job -EventName StateChanged -Action {
                    if ($EventArgs.NewState -eq 'Completed' -or $EventArgs.NewState -eq 'Failed') {
                        Remove-Job $Event.Sender -Force -ErrorAction SilentlyContinue
                    }
                } | Out-Null
            }
            catch {
                # Silently ignore cleanup failures
            }
        }
    }
}


# ----------------------------------------------------------
# Banner
# ----------------------------------------------------------

Write-Banner


# ----------------------------------------------------------
# Fetch latest release
# ----------------------------------------------------------

Write-Step "Checking for latest version..."

try {
    $Release = Invoke-RestMethod `
        -Uri $ApiUrl `
        -Headers $Headers `
        -ErrorAction Stop
}
catch {
    $errorId = $_.Exception.InnerException.ErrorId

    if ($errorId -eq 'WebException' -or $_.Exception -is [System.Net.WebException]) {
        Write-ErrorMessage "Unable to connect to GitHub."
        Write-Host "  Please check your internet connection and try again." -ForegroundColor DarkGray
    }
    elseif ($_.Exception.Message -match "403") {
        Write-ErrorMessage "GitHub API rate limit exceeded."
        Write-Host "  Please wait a few minutes and try again." -ForegroundColor DarkGray
    }
    else {
        Write-ErrorMessage "Unable to fetch release information."
        Write-Host "  GitHub may be temporarily unavailable." -ForegroundColor DarkGray
    }

    Exit-Installer 1
}


$Version = $Release.tag_name.TrimStart("v")


# ----------------------------------------------------------
# Find installer EXE
# ----------------------------------------------------------

Write-Step "Searching for installer..."

$AllExeAssets = $Release.assets | Where-Object {
    $_.name -match "\.exe$"
}

$PreferredNames = @("Setup", "Installer", "Install")

$InstallerAsset = $AllExeAssets |
    Where-Object {
        $name = $_.name
        -not ($name -match "portable") -and
        -not ($name -match "debug") -and
        -not ($name -match "symbol") -and
        ($PreferredNames | Where-Object { $name -match $_ })
    } |
    Select-Object -First 1

if (-not $InstallerAsset) {
    $InstallerAsset = $AllExeAssets |
        Where-Object {
            $_.name -notmatch "portable" -and
            $_.name -notmatch "debug" -and
            $_.name -notmatch "symbol"
        } |
        Select-Object -First 1
}

if (-not $InstallerAsset) {
    Write-ErrorMessage "No setup installer found in the latest release."
    Exit-Installer 1
}


$DownloadUrl = $InstallerAsset.browser_download_url


Write-Host ""
Write-Info "Version" "v$Version"
Write-Info "Release" "$($Release.published_at)"
Write-Info "File" "$($InstallerAsset.name)"

if ($InstallerAsset.size) {
    Write-Info "Size" (Format-FileSize $InstallerAsset.size)
}


# ----------------------------------------------------------
# Download installer
# ----------------------------------------------------------

$InstallerFile = Join-Path `
    $env:TEMP `
    "$AppName-Setup-$Version.exe"

Write-Step "Downloading installer..."

try {

    Add-Type -AssemblyName System.Net.Http

    $Client = New-Object System.Net.Http.HttpClient

    foreach ($key in $Headers.Keys) {
        $Client.DefaultRequestHeaders.Add($key, $Headers[$key])
    }

    $Client.Timeout = [TimeSpan]::FromMinutes(15)

    $Response = $Client.GetAsync(
        $DownloadUrl,
        [System.Net.Http.HttpCompletionOption]::ResponseHeadersRead
    ).Result


    if (-not $Response.IsSuccessStatusCode) {
        throw "HTTP $($Response.StatusCode)"
    }


    $TotalBytes = $Response.Content.Headers.ContentLength

    $Stream = $Response.Content.ReadAsStreamAsync().Result

    $FileStream = [System.IO.File]::Create($InstallerFile)


    $Buffer = New-Object byte[] 8192
    $DownloadedBytes = 0
    $LastProgressUpdate = 0


    while (($Read = $Stream.Read($Buffer, 0, $Buffer.Length)) -gt 0) {

        $FileStream.Write($Buffer, 0, $Read)

        $DownloadedBytes += $Read

        $Now = [datetime]::Now.Ticks
        if ($Now - $LastProgressUpdate -gt 5000000) {
            $LastProgressUpdate = $Now

            if ($TotalBytes -and $TotalBytes -gt 0) {

                $Percent = [math]::Floor(
                    ($DownloadedBytes / $TotalBytes) * 100
                )

                $BarLength = 30
                $Filled = [math]::Floor(
                    ($Percent / 100) * $BarLength
                )

                $Bar =
                    ("=" * $Filled) +
                    ("-" * ($BarLength - $Filled))

                $Downloaded = Format-FileSize $DownloadedBytes
                $Total = Format-FileSize $TotalBytes

                Write-Host -NoNewline "`r  [*] $Downloaded / $Total  " -ForegroundColor Cyan
                Write-Host -NoNewline "[$Bar] " -ForegroundColor Green
                Write-Host -NoNewline "$Percent%" -ForegroundColor Yellow
            }
            else {

                $Downloaded = Format-FileSize $DownloadedBytes

                $BarLength = 30
                $Pulse = $DownloadedBytes % ($BarLength * 2)

                $Left = $Pulse % $BarLength
                $Bar = (" " * $Left) + ("*" * 2) + (" " * ($BarLength - $Left - 2))

                Write-Host -NoNewline "`r  [*] $Downloaded downloaded  " -ForegroundColor Cyan
                Write-Host -NoNewline "[$Bar]" -ForegroundColor Green
            }
        }
    }

    if ($TotalBytes -and $TotalBytes -gt 0) {
        $FinalDownloaded = Format-FileSize $TotalBytes
        $FinalTotal = Format-FileSize $TotalBytes

        Write-Host -NoNewline "`r  [*] $FinalDownloaded / $FinalTotal  " -ForegroundColor Cyan
        Write-Host -NoNewline "[$("=" * 30)] " -ForegroundColor Green
        Write-Host -NoNewline "100%" -ForegroundColor Yellow
    }


    $FileStream.Close()
    $Stream.Close()
    $Client.Dispose()


    Write-Host ""
    Write-Success "Download completed."

}
catch {

    Write-Host ""
    Write-ErrorMessage "Download failed."

    if ($_.Exception.Message -match "timeout" -or $_.Exception.Message -match "timed out") {
        Write-Host "  The download timed out. Please check your connection." -ForegroundColor DarkGray
    }
    elseif ($_.Exception.Message -match "refused" -or $_.Exception.Message -match "resolution") {
        Write-Host "  Unable to reach GitHub. Please check your internet." -ForegroundColor DarkGray
    }
    else {
        Write-Host "  Please check your internet connection and try again." -ForegroundColor DarkGray
    }

    Cleanup $InstallerFile
    Exit-Installer 1
}


# ----------------------------------------------------------
# Verify download
# ----------------------------------------------------------

if (-not (Test-Path $InstallerFile)) {
    Write-ErrorMessage "Downloaded file not found."
    Cleanup $InstallerFile
    Exit-Installer 1
}

$fileInfo = Get-Item $InstallerFile
if ($fileInfo.Length -eq 0) {
    Write-ErrorMessage "Downloaded file is empty."
    Cleanup $InstallerFile
    Exit-Installer 1
}


# ----------------------------------------------------------
# Run installer wizard
# ----------------------------------------------------------

Write-Step "Starting setup wizard..."

try {

    $Process = Start-Process `
        -FilePath $InstallerFile `
        -PassThru `
        -ErrorAction Stop

    while (-not $Process.HasExited) {
        Start-Sleep -Milliseconds 500
        $Process.Refresh()
    }


    $ExitCode = $Process.ExitCode

    switch ($ExitCode) {

        0 {
            Write-Host ""
            Write-Success "FitFetch has been installed successfully."
        }

        2 {
            Write-Host ""
            Write-WarningMessage "Installation was cancelled."
        }

        default {
            Write-Host ""
            Write-ErrorMessage "Setup wizard encountered an error."
            Write-Host "  Please try running the installer again." -ForegroundColor DarkGray
        }
    }

}
catch {

    Write-ErrorMessage "Failed to start the setup wizard."
    Write-Host "  The installer may require administrator privileges." -ForegroundColor DarkGray

    Cleanup $InstallerFile
    Exit-Installer 1
}


# ----------------------------------------------------------
# Cleanup
# ----------------------------------------------------------

Cleanup $InstallerFile


# ----------------------------------------------------------
# Finish
# ----------------------------------------------------------

Exit-Installer 0
