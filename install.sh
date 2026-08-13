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

# 4. Define installation directory
INSTALL_DIR="$HOME/.mini-ci"
if [ -d "$INSTALL_DIR" ]; then
    echo "🧹 Cleaning up previous installation..."
    rm -rf "$INSTALL_DIR"
fi

# 5. Clone and Install
echo "📦 Downloading source code..."
git clone https://github.com/mosakrm0/Plan-Tool.git "$INSTALL_DIR" --quiet

echo "🔧 Installing via pip..."
cd "$INSTALL_DIR"
# We use standard install here, not -e (editable), since it's for an end-user
python3 -m pip install . --quiet

echo ""
echo "✅ Installation complete!"
echo "You can now run your CI engine from anywhere by typing: plan --help"