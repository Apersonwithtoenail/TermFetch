#!/bin/bash
set -e
SRC="$(cd "$(dirname "$0")" && pwd)"
DEST="$HOME/.local/bin"

mkdir -p "$DEST"
chmod +x "$SRC/termfetch.py"
ln -sf "$SRC/termfetch.py" "$DEST/termfetch"

echo "✅ installed: $DEST/termfetch"
if ! echo ":$PATH:" | grep -q ":$DEST:"; then
    echo ""
    echo "⚠  $DEST is not in your PATH."
    echo "   Add to ~/.zshrc:  export PATH=\"\$HOME/.local/bin:\$PATH\""
fi
