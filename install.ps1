Write-Host "Installing Plan..." -ForegroundColor Cyan

# 1. Check for Python
if (-Not (Get-Command "python" -ErrorAction SilentlyContinue)) {
    Write-Host "❌ Error: Python is required but not installed." -ForegroundColor Red
    exit 1
}

# 2. Check for Docker
if (-Not (Get-Command "docker" -ErrorAction SilentlyContinue)) {
    Write-Host "❌ Error: Docker is required but not installed. Please install Docker Desktop." -ForegroundColor Red
    exit 1
}

# 3. Check for Git
if (-Not (Get-Command "git" -ErrorAction SilentlyContinue)) {
    Write-Host "❌ Error: Git is required to download the source." -ForegroundColor Red
    exit 1
}

# 4. Define installation directory
$InstallDir = "$env:USERPROFILE\.mini-ci"
if (Test-Path $InstallDir) {
    Write-Host "🧹 Cleaning up previous installation..." -ForegroundColor Gray
    Remove-Item -Recurse -Force $InstallDir
}

# 5. Clone and Install
Write-Host "📦 Downloading source code..." -ForegroundColor Gray
git clone https://github.com/mosakrm0/Plan-Tool.git $InstallDir

Write-Host "🔧 Installing via pip..." -ForegroundColor Gray
Set-Location $InstallDir
python -m pip install . 

Write-Host "`n✅ Installation complete!" -ForegroundColor Green
Write-Host "You can now run your CI engine from anywhere by typing: plan --help" -ForegroundColor Green