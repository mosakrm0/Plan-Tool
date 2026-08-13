Write-Host "Installing Plan..." -ForegroundColor Cyan

# 1. Check Prerequisites
if (-Not (Get-Command "python" -ErrorAction SilentlyContinue)) { Write-Host "❌ Python is missing." -ForegroundColor Red; exit 1 }
if (-Not (Get-Command "git" -ErrorAction SilentlyContinue)) { Write-Host "❌ Git is missing." -ForegroundColor Red; exit 1 }

# 2. Clone Repository
$InstallDir = "$env:USERPROFILE\.mini-ci"
if (Test-Path $InstallDir) { Remove-Item -Recurse -Force $InstallDir }
git clone https://github.com/mosakrm0/Plan-Tool.git $InstallDir --quiet

# 3. Setup Isolated Virtual Environment
Write-Host "📦 Setting up isolated Python environment..." -ForegroundColor Gray
sudo apt install python3.13-venv
python -m venv "$InstallDir\venv"

# 4. Install using the isolated pip
Write-Host "🔧 Installing dependencies..." -ForegroundColor Gray
Set-Location $InstallDir
& "$InstallDir\venv\Scripts\pip.exe" install --quiet .

# 5. Create Global Wrappers & Fix PATH
$BinDir = Join-Path $InstallDir "bin"
New-Item -ItemType Directory -Force -Path $BinDir | Out-Null

# Wrapper for CMD / PowerShell
$CmdWrapper = Join-Path $BinDir "plan.cmd"
Set-Content -Path $CmdWrapper -Value "@echo off`n`"$InstallDir\venv\Scripts\plan.exe`" %*"

# Wrapper for Fish / Git Bash (No extension)
$FishWrapper = Join-Path $BinDir "plan"
Set-Content -Path $FishWrapper -Value "#!/usr/bin/env sh`n`"$InstallDir/venv/Scripts/plan.exe`" `"`$@`""
(Get-Content $FishWrapper) -join "`n" | Set-Content -NoNewline $FishWrapper

# Safely inject into Windows Registry PATH
$Key = [Microsoft.Win32.Registry]::CurrentUser.OpenSubKey("Environment", $true)
$CurrentPath = $Key.GetValue("Path", "", [Microsoft.Win32.RegistryValueOptions]::DoNotExpandEnvironmentNames)

if ($CurrentPath -notmatch [regex]::Escape($BinDir)) {
    $NewPath = $CurrentPath + ";" + $BinDir
    $Key.SetValue("Path", $NewPath, [Microsoft.Win32.RegistryValueKind]::ExpandString)
}
$Key.Close()

Write-Host "`n✅ Installation complete!" -ForegroundColor Green
Write-Host "⚠️  IMPORTANT: Close this terminal and open a new one to refresh your PATH." -ForegroundColor Yellow