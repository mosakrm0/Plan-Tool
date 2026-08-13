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

# 4. Check for and install pipx
if (-Not (Get-Command "pipx" -ErrorAction SilentlyContinue)) {
    Write-Host "📥 Installing pipx..." -ForegroundColor Gray
    python -m pip install --user pipx
    
    # Add pipx to PATH if not already there
    $env:Path += ";$env:APPDATA\Python\Scripts"
}

# 5. Check for and install pipenv via pipx
if (-Not (Get-Command "pipenv" -ErrorAction SilentlyContinue)) {
    Write-Host "📥 Installing pipenv via pipx..." -ForegroundColor Gray
    pipx install pipenv
}

# 6. Define installation directory
$InstallDir = "$env:USERPROFILE\.mini-ci"
if (Test-Path $InstallDir) {
    Write-Host "🧹 Cleaning up previous installation..." -ForegroundColor Gray
    Remove-Item -Recurse -Force $InstallDir
}

# 7. Clone and Install
Write-Host "📦 Downloading source code..." -ForegroundColor Gray
git clone https://github.com/mosakrm0/Plan-Tool.git $InstallDir

Write-Host "🔧 Installing dependencies with pipenv..." -ForegroundColor Gray
Set-Location $InstallDir
pipenv install 

Write-Host "`n✅ Installation complete!" -ForegroundColor Green
Write-Host "You can now run your CI engine from anywhere by typing: plan --help" -ForegroundColor Green