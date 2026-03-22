#!/bin/bash
# overlayRoot.sh — pivot root to an overlayfs (tmpfs upper) before init
# Runs as init= from kernel cmdline, or sourced from initramfs hook.
# Lower:  real rootfs (read-only ext4 on SD card)
# Upper:  tmpfs (lost on reboot — keeps SD card protected)
# Work:   required by overlayfs kernel module

# This script is invoked very early (before systemd) via:
#   /boot/cmdline.txt: init=/usr/local/sbin/overlayRoot.sh

# If OVERLAYROOT_DISABLE is set (e.g. via boot param), skip overlay and boot normally.
for param in $(cat /proc/cmdline 2>/dev/null); do
  case "$param" in
    overlayroot=disabled) exec /sbin/init "$@" ;;
  esac
done

# Mount required pseudo filesystems
mount -t proc proc /proc
mount -t sysfs sysfs /sys
mount -t devtmpfs devtmpfs /dev 2>/dev/null || true

# Find the real root device from /proc/cmdline
ROOT_DEVICE=$(grep -o 'root=[^ ]*' /proc/cmdline | cut -d= -f2-)
ROOT_FSTYPE=$(grep -o 'rootfstype=[^ ]*' /proc/cmdline | cut -d= -f2 || echo "ext4")

# Wait for root device to appear (SD cards may be slow)
TIMEOUT=30
COUNT=0
while [ ! -b "$ROOT_DEVICE" ] && [ $COUNT -lt $TIMEOUT ]; do
  # Try resolving PARTUUID
  if echo "$ROOT_DEVICE" | grep -q "PARTUUID="; then
    PUUID=$(echo "$ROOT_DEVICE" | sed 's/PARTUUID=//')
    RESOLVED=$(blkid -t PARTUUID="$PUUID" -o device 2>/dev/null || true)
    [ -n "$RESOLVED" ] && ROOT_DEVICE="$RESOLVED" && break
  fi
  sleep 1
  COUNT=$((COUNT + 1))
done

# Mount the real root read-only
mkdir -p /mnt/lower
mount -o ro,noatime -t "$ROOT_FSTYPE" "$ROOT_DEVICE" /mnt/lower

# Set up tmpfs for upper + work directories
mkdir -p /mnt/upper
mount -t tmpfs -o size=50%,mode=755 tmpfs /mnt/upper
mkdir -p /mnt/upper/upper /mnt/upper/work

# Mount the overlay
mkdir -p /mnt/overlay
mount -t overlay overlay \
  -o lowerdir=/mnt/lower,upperdir=/mnt/upper/upper,workdir=/mnt/upper/work \
  /mnt/overlay

# Pivot root into the overlay
mkdir -p /mnt/overlay/mnt/lower /mnt/overlay/mnt/upper
pivot_root /mnt/overlay /mnt/overlay/mnt/lower

# Move mounts into new root
mount --move /mnt/lower/proc /proc   2>/dev/null || mount -t proc proc /proc
mount --move /mnt/lower/sys  /sys    2>/dev/null || mount -t sysfs sysfs /sys
mount --move /mnt/lower/dev  /dev    2>/dev/null || mount -t devtmpfs devtmpfs /dev

# Hand off to systemd
exec /sbin/init "$@"
