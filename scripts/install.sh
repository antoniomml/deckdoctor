#!/bin/sh
# Install DeckDoctor into ~/.local/bin without pacman, Flatpak, or Decky.
# Verifies the GitHub Release SHA256SUMS file unless DECKDOCTOR_SKIP_VERIFY=1.
set -eu

REPO="${DECKDOCTOR_REPO:-antoniomml/deckdoctor}"
PREFIX="${PREFIX:-$HOME/.local/bin}"
URL="${DECKDOCTOR_URL:-https://github.com/${REPO}/releases/latest/download/deckdoctor}"
SUMS_URL="${DECKDOCTOR_SUMS_URL:-https://github.com/${REPO}/releases/latest/download/SHA256SUMS}"

mkdir -p "$PREFIX"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

echo "Downloading $URL → $TMP/deckdoctor"
curl -fL "$URL" -o "$TMP/deckdoctor"

if [ "${DECKDOCTOR_SKIP_VERIFY:-0}" != "1" ]; then
  if ! command -v sha256sum >/dev/null 2>&1; then
    echo "sha256sum is required to verify the download. Install coreutils or set DECKDOCTOR_SKIP_VERIFY=1" >&2
    exit 1
  fi
  echo "Downloading $SUMS_URL"
  curl -fL "$SUMS_URL" -o "$TMP/SHA256SUMS"
  # Accept "HASH  deckdoctor" or "HASH  ./deckdoctor"
  if ! grep -E '[[:space:]](\./)?deckdoctor$' "$TMP/SHA256SUMS" > "$TMP/SHA256SUMS.one"; then
    echo "SHA256SUMS does not mention deckdoctor" >&2
    exit 1
  fi
  (
    cd "$TMP"
    sha256sum -c SHA256SUMS.one
  )
fi

chmod 755 "$TMP/deckdoctor"
cp "$TMP/deckdoctor" "$PREFIX/deckdoctor"

echo "Installed $PREFIX/deckdoctor"
case ":${PATH}:" in
  *:"$PREFIX":*) ;;
  *)
    echo "Warning: $PREFIX is not on PATH. Add it, then run: deckdoctor"
    echo "  export PATH=\"$PREFIX:\$PATH\""
    ;;
esac
echo "Then run: deckdoctor"
echo "PyInstaller onefile extracts on first start; that can take a few seconds."
