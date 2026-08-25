#!/bin/sh
# Install DeckDoctor into ~/.local/bin without pacman, Flatpak, or Decky.
set -eu

REPO="${DECKDOCTOR_REPO:-antoniomml/deckdoctor}"

PREFIX="${PREFIX:-$HOME/.local/bin}"
mkdir -p "$PREFIX"

URL="${DECKDOCTOR_URL:-https://github.com/${REPO}/releases/latest/download/deckdoctor}"

echo "Downloading $URL → $PREFIX/deckdoctor"
curl -fL "$URL" -o "$PREFIX/deckdoctor"
chmod 755 "$PREFIX/deckdoctor"

echo "Installed $PREFIX/deckdoctor"
echo "Make sure $PREFIX is on your PATH, then run: deckdoctor"
