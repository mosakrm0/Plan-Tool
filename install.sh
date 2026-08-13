#!/usr/bin/env bash
set -e

echo "Installing Plan..."

# 1. Check for Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 is required but not installed."
    exit 1
fi

# 2. Check for Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Error: Docker is required but not installed. Please install Docker Desktop or Engine."
    exit 1
fi

# 3. Check for Git
if ! command -v git &> /dev/null; then
    echo "❌ Error: Git is required to download the source."
    exit 1
fi

# 4. Check for and install pipx
if ! command -v pipx &> /dev/null; then
    echo "📥 Installing pipx..."
    python3 -m pip install --user pipx
    
    # Add pipx to PATH if not already there
    export PATH="$PATH:$HOME/.local/bin"
fi

# 5. Check for and install pipenv via pipx
if ! command -v pipenv &> /dev/null; then
    echo "📥 Installing pipenv via pipx..."
    pipx install pipenv
fi

# 6. Define installation directory
INSTALL_DIR="$HOME/.mini-ci"
if [ -d "$INSTALL_DIR" ]; then
    echo "🧹 Cleaning up previous installation..."
    rm -rf "$INSTALL_DIR"
fi

# 7. Clone and Install
echo "📦 Downloading source code..."
git clone https://github.com/mosakrm0/Plan-Tool.git "$INSTALL_DIR" --quiet

echo "🔧 Installing dependencies with pipenv..."
cd "$INSTALL_DIR"
pipenv install

echo ""
echo "✅ Installation complete!"
echo "You can now run your CI engine from anywhere by typing: plan --help"