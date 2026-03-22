#!/bin/bash
# Shrink a built .img file using PiShrink
# Usage: ./os/shrink-image.sh path/to/image.img
set -e

IMG="$1"
[ -z "$IMG" ] && { echo "Usage: $0 <image.img>"; exit 1; }
[ -f "$IMG" ]  || { echo "Error: file not found: $IMG"; exit 1; }

PISHRINK_URL="https://raw.githubusercontent.com/Drewsif/PiShrink/master/pishrink.sh"

if ! command -v pishrink.sh &>/dev/null; then
  echo "Downloading PiShrink..."
  curl -fsSL "$PISHRINK_URL" -o /tmp/pishrink.sh
  chmod +x /tmp/pishrink.sh
  PISHRINK=/tmp/pishrink.sh
else
  PISHRINK=pishrink.sh
fi

echo "Shrinking $IMG ..."
sudo "$PISHRINK" -Za "$IMG"
echo "Done. Shrunk image: ${IMG%.img}-shrunk.img.xz"
