#!/bin/bash
set -e
SRC="$(cd "$(dirname "$0")" && pwd)"
DEST="$HOME/.local/bin"

mkdir -p "$DEST"
chmod +x "$SRC/termfetch.py"
ln -sf "$SRC/termfetch.py" "$DEST/termfetch"


# icon
cp "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/assets/icon.svg" "$HOME/.local/share/icons/hicolor/scalable/apps/termfetch.svg" 2>/dev/null || true
gtk-update-icon-cache -f -t "$HOME/.local/share/icons/hicolor" 2>/dev/null || true

echo "✅ installed: $DEST/termfetch"
if ! echo ":$PATH:" | grep -q ":$DEST:"; then
    echo ""
    echo "⚠  $DEST is not in your PATH."
    echo "   Add to ~/.zshrc:  export PATH=\"\$HOME/.local/bin:\$PATH\""
fi
