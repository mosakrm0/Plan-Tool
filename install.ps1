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

# 4. Bootstrap pipenv installation
if (-Not (Get-Command "pipenv" -ErrorAction SilentlyContinue)) {
    Write-Host "📥 Installing pipenv..." -ForegroundColor Gray
    
    # Create a temporary virtual environment to bootstrap pipenv
    $TempVenv = [System.IO.Path]::Combine([System.IO.Path]::GetTempPath(), [System.IO.Path]::GetRandomFileName())
    python -m venv $TempVenv
    & "$TempVenv\Scripts\Activate.ps1"
    pip install pipenv
    deactivate
    
    # Add temp venv to PATH for this session
    $env:Path = "$TempVenv\Scripts;$env:Path"
}

# 5. Define installation directory
$InstallDir = "$env:USERPROFILE\.mini-ci"
if (Test-Path $InstallDir) {
    Write-Host "🧹 Cleaning up previous installation..." -ForegroundColor Gray
    Remove-Item -Recurse -Force $InstallDir
}

# 6. Clone and Install
Write-Host "📦 Downloading source code..." -ForegroundColor Gray
git clone https://github.com/mosakrm0/Plan-Tool.git $InstallDir

Write-Host "🔧 Installing dependencies with pipenv..." -ForegroundColor Gray
Set-Location $InstallDir
pipenv install 

Write-Host "`n✅ Installation complete!" -ForegroundColor Green
Write-Host "You can now run your CI engine from anywhere by typing: plan --help" -ForegroundColor Green