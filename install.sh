#!/usr/bin/env bash
set -e

echo " Installing Plan..."

# 1. Check Prerequisites
if ! command -v python3 &> /dev/null; then echo "❌ Python 3 missing."; exit 1; fi
if ! command -v git &> /dev/null; then echo "❌ Git missing."; exit 1; fi

# 2. Setup Directories
INSTALL_DIR="$HOME/.plan"
SRC_DIR="$INSTALL_DIR/src"

if [ -d "$INSTALL_DIR" ]; then 
    echo "🧹 Cleaning up previous installation..."
    rm -rf "$INSTALL_DIR"
fi

# 3. Clone Repository into a temporary source folder
git clone https://github.com/mosakrm0/Plan-Tool.git "$SRC_DIR" --quiet

# 4. Setup Isolated Virtual Environment 
echo "📦 Setting up isolated Python environment..."
sudo apt install python3.13-venv -y
python3 -m venv "$INSTALL_DIR/venv"

# 5. Install using the isolated pip
echo "🔧 Installing dependencies..."
"$INSTALL_DIR/venv/bin/pip" install --quiet "$SRC_DIR"

# 6. Delete the raw source files to save space
echo "🧹 Removing raw source files..."
rm -rf "$SRC_DIR"

# 7. Create Global Wrapper & Fix PATH
BIN_DIR="$INSTALL_DIR/bin"
mkdir -p "$BIN_DIR"

WRAPPER_SCRIPT="$BIN_DIR/plan"
cat << EOF > "$WRAPPER_SCRIPT"
#!/usr/bin/env bash
exec "$INSTALL_DIR/venv/bin/plan" "\$@"
EOF
chmod +x "$WRAPPER_SCRIPT"

PATH_EXPORT="export PATH=\"\$PATH:$BIN_DIR\""
FISH_EXPORT="set -gx PATH \$PATH $BIN_DIR"

# Inject into Bash
if [ -f "$HOME/.bashrc" ] && ! grep -q "$BIN_DIR" "$HOME/.bashrc"; then
    echo "$PATH_EXPORT" >> "$HOME/.bashrc"
fi

# Inject into Zsh (macOS Default)
if [ -f "$HOME/.zshrc" ] && ! grep -q "$BIN_DIR" "$HOME/.zshrc"; then
    echo "$PATH_EXPORT" >> "$HOME/.zshrc"
fi

# Inject into Fish
if [ -d "$HOME/.config/fish" ] && ! grep -q "$BIN_DIR" "$HOME/.config/fish/config.fish" 2>/dev/null; then
    echo "$FISH_EXPORT" >> "$HOME/.config/fish/config.fish"
fi

echo ""
echo "✅ Installation complete!"
echo "⚠️  IMPORTANT: Close this terminal and open a new one to refresh your PATH."