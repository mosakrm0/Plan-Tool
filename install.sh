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

# 4. Bootstrap pipenv installation
if ! command -v pipenv &> /dev/null; then
    echo "📥 Installing pipenv..."
    
    # Create a temporary virtual environment to bootstrap pipenv
    TEMP_VENV=$(mktemp -d)
    python3 -m venv "$TEMP_VENV"
    source "$TEMP_VENV/bin/activate"
    pip install --quiet pipenv
    deactivate
    
    # Add temp venv to PATH for this session
    export PATH="$TEMP_VENV/bin:$PATH"
fi

# 5. Define installation directory
INSTALL_DIR="$HOME/.mini-ci"
if [ -d "$INSTALL_DIR" ]; then
    echo "🧹 Cleaning up previous installation..."
    rm -rf "$INSTALL_DIR"
fi

# 6. Clone and Install
echo "📦 Downloading source code..."
git clone https://github.com/mosakrm0/Plan-Tool.git "$INSTALL_DIR" --quiet

echo "🔧 Installing dependencies with pipenv..."
cd "$INSTALL_DIR"
pipenv install

echo ""
echo "✅ Installation complete!"
echo "You can now run your CI engine from anywhere by typing: plan --help"