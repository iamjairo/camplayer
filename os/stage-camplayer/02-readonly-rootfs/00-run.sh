#!/bin/bash -e
# Configure overlayfs read-only root filesystem
# Based on the technique from the original Camplayer OS
# and Raspberry Pi's own read-only filesystem overlay

STAGE_WORK_DIR="$(dirname "$0")"

on_chroot << EOF
set -e
# Install overlayroot for tmpfs overlay support
apt-get install -y --no-install-recommends overlayroot

# Configure overlayroot to use tmpfs
# swap=1: also overlay /var/swap; recurse=0: only overlay root
echo 'overlayroot="tmpfs:swap=1,recurse=0"' >> /etc/overlayroot.conf
EOF

# Install our overlay init script (runs from initramfs before real init)
install -m 755 "${STAGE_WORK_DIR}/files/overlayRoot.sh" \
  "${ROOTFS_DIR}/usr/local/sbin/overlayRoot.sh"

# Install custom fstab
install -m 644 "${STAGE_WORK_DIR}/files/fstab" "${ROOTFS_DIR}/etc/fstab"

on_chroot << EOF
set -e
# Rebuild initramfs to include overlayroot support
update-initramfs -u || true
EOF

echo "Stage 02-readonly-rootfs complete."
