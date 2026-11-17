#!/bin/bash
# Setup script for mail-auto-draft skill
# Installs processor, systemd units, and configuration

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_DIR="$HOME/.config/mail-auto-draft"
BIN_DIR="$HOME/.local/bin"
DATA_DIR="$HOME/.local/share/mail-auto-draft"
SYSTEMD_USER_DIR="$HOME/.config/systemd/user"

echo "Mail auto-draft skill setup"
echo "==========================="
echo ""

# Check prerequisites
echo "[1/5] Checking prerequisites..."
for cmd in himalaya python3 systemctl flock; do
    if ! command -v "$cmd" &> /dev/null; then
        echo "ERROR: Required command not found: $cmd"
        exit 1
    fi
done
echo "✓ All prerequisites found"
echo ""

# Create directories
echo "[2/5] Creating directories..."
mkdir -p "$CONFIG_DIR"
mkdir -p "$BIN_DIR"
mkdir -p "$DATA_DIR"
mkdir -p "$SYSTEMD_USER_DIR"
echo "✓ Directories created"
echo ""

# Install processor
echo "[3/5] Installing processor..."
if [ -f "$SCRIPT_DIR/process_inbox.py" ]; then
    cp "$SCRIPT_DIR/process_inbox.py" "$BIN_DIR/"
    chmod 755 "$BIN_DIR/process_inbox.py"
    echo "✓ Processor installed to $BIN_DIR/process_inbox.py"
else
    echo "ERROR: process_inbox.py not found in $SCRIPT_DIR"
    exit 1
fi
echo ""

# Install configuration
echo "[4/5] Installing configuration..."
if [ ! -f "$CONFIG_DIR/config.yaml" ]; then
    if [ -f "$SCRIPT_DIR/mail-auto-draft-config.yaml" ]; then
        cp "$SCRIPT_DIR/mail-auto-draft-config.yaml" "$CONFIG_DIR/config.yaml"
        echo "✓ Config template installed to $CONFIG_DIR/config.yaml"
        echo "  IMPORTANT: Edit this file to add your email addresses and whitelist"
    else
        echo "ERROR: mail-auto-draft-config.yaml not found"
        exit 1
    fi
else
    echo "⚠ Config already exists at $CONFIG_DIR/config.yaml (not overwriting)"
fi
echo ""

# Install systemd units
echo "[5/5] Installing systemd user units..."
for unit in "$SCRIPT_DIR/mail-auto-draft.service" "$SCRIPT_DIR/mail-auto-draft.timer"; do
    if [ ! -f "$unit" ]; then
        echo "ERROR: Systemd unit not found: $unit"
        exit 1
    fi
    cp "$unit" "$SYSTEMD_USER_DIR/"
    echo "✓ Installed $(basename "$unit")"
done
echo ""

# Reload systemd
echo "Reloading systemd user daemon..."
systemctl --user daemon-reload
echo ""

# Show next steps
echo "Setup complete!"
echo "==============="
echo ""
echo "Next steps:"
echo ""
echo "1. Edit configuration:"
echo "   $CONFIG_DIR/config.yaml"
echo "   - Set your own_addresses"
echo "   - Set whitelist_senders"
echo "   - Keep auto_send_enabled: false initially"
echo ""
echo "2. Test the processor (dry-run mode):"
echo "   $BIN_DIR/process_inbox.py --dry-run"
echo ""
echo "3. Check the log:"
echo "   tail -f $DATA_DIR/processor.log"
echo ""
echo "4. Enable the systemd timer (runs every 5 minutes):"
echo "   systemctl --user enable mail-auto-draft.timer"
echo "   systemctl --user start mail-auto-draft.timer"
echo ""
echo "5. Check timer status:"
echo "   systemctl --user status mail-auto-draft.timer"
echo ""
echo "6. After testing, enable auto-send in config.yaml:"
echo "   auto_send_enabled: true"
echo ""
echo "IMPORTANT: Keep auto_send_enabled: false during initial testing!"
echo ""
