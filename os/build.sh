#!/bin/bash
# Build Camplayer OS image using pi-gen
# Usage: ./os/build.sh [--no-clean]
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
PIGEN_DIR="/tmp/pi-gen"
STAGE_DIR="$SCRIPT_DIR/stage-camplayer"

# ── Clone pi-gen if needed ─────────────────────────────────────────────────
if [ ! -d "$PIGEN_DIR" ]; then
  echo "Cloning pi-gen (bookworm branch)..."
  git clone --depth=1 --branch bookworm \
    https://github.com/RPi-Distro/pi-gen.git "$PIGEN_DIR"
fi

# ── Configure pi-gen ───────────────────────────────────────────────────────
cat > "$PIGEN_DIR/config" << 'CONFIG'
IMG_NAME="CamplayerOS"
RELEASE="bookworm"
DEPLOY_COMPRESSION="xz"
LOCALE_DEFAULT="en_US.UTF-8"
TARGET_HOSTNAME="camplayer"
KEYBOARD_KEYMAP="us"
KEYBOARD_LAYOUT="English (US)"
TIMEZONE_DEFAULT="America/New_York"
FIRST_USER_NAME="pi"
FIRST_USER_PASS="camplayer"
ENABLE_SSH=1
STAGE_LIST="stage0 stage1 stage2 stage-camplayer"
CONFIG

# ── Disable unwanted pi-gen stages ────────────────────────────────────────
touch "$PIGEN_DIR/stage3/SKIP" 2>/dev/null || true
touch "$PIGEN_DIR/stage4/SKIP" 2>/dev/null || true
touch "$PIGEN_DIR/stage5/SKIP" 2>/dev/null || true
# Produce image only from our custom stage, not from intermediate stage2
touch "$PIGEN_DIR/stage2/SKIP_IMAGES" 2>/dev/null || true

# ── Copy our custom stage into pi-gen ─────────────────────────────────────
rm -rf "$PIGEN_DIR/stage-camplayer"
cp -r "$STAGE_DIR" "$PIGEN_DIR/stage-camplayer"

# ── Embed repo source so 00-run.sh can install it ─────────────────────────
SRC_DEST="$PIGEN_DIR/stage-camplayer/01-camplayer-install/files/camplayer-src"
rm -rf "$SRC_DEST"
rsync -a \
  --exclude='.git' \
  --exclude='node_modules' \
  --exclude='*.img' \
  --exclude='*.img.xz' \
  --exclude='os/stage-camplayer/01-camplayer-install/files/camplayer-src' \
  "$REPO_ROOT/" "$SRC_DEST/"

# ── Run the pi-gen build ───────────────────────────────────────────────────
cd "$PIGEN_DIR"
if [[ "$1" == "--no-clean" ]]; then
  CLEAN=0 bash build.sh
else
  bash build.sh
fi

# ── Announce the output ────────────────────────────────────────────────────
IMG=$(ls deploy/CamplayerOS-*.img.xz 2>/dev/null | head -1 || true)
if [ -n "$IMG" ]; then
  echo ""
  echo "✅ Build complete: $IMG"
  echo "   Flash with: xzcat $IMG | sudo dd of=/dev/sdX bs=4M status=progress"
  echo "   Or use balenaEtcher."
else
  echo "⚠️  Build finished but no .img.xz found in deploy/. Check pi-gen output."
  exit 1
fi
