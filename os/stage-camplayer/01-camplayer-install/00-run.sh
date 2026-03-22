#!/bin/bash -e
# Install camplayer to the target rootfs

STAGE_WORK_DIR="$(dirname "$0")"

# ── Copy repo source into the target rootfs ──────────────────────────────────
install -d "${ROOTFS_DIR}/usr/local/share/camplayer"
rsync -a --exclude='.git' --exclude='node_modules' --exclude='*.img' --exclude='*.img.xz' \
  "${STAGE_WORK_DIR}/files/camplayer-src/" \
  "${ROOTFS_DIR}/usr/local/share/camplayer/"

# ── Build React frontend (runs on the build host, not in chroot) ─────────────
FRONTEND_SRC="${STAGE_WORK_DIR}/files/camplayer-src/web/frontend"
if [ -d "$FRONTEND_SRC" ] && [ -f "$FRONTEND_SRC/package.json" ]; then
  echo "Building React frontend..."
  pushd "$FRONTEND_SRC"
  npm ci
  npm run build
  popd
  install -d "${ROOTFS_DIR}/usr/local/share/camplayer/web/dist"
  rsync -a "$FRONTEND_SRC/dist/" \
    "${ROOTFS_DIR}/usr/local/share/camplayer/web/dist/"
fi

# ── Install helper scripts ───────────────────────────────────────────────────
install -m 755 "${STAGE_WORK_DIR}/files/os_readonly"             "${ROOTFS_DIR}/usr/local/bin/os_readonly"
install -m 755 "${STAGE_WORK_DIR}/files/os_readwrite"            "${ROOTFS_DIR}/usr/local/bin/os_readwrite"
install -m 755 "${STAGE_WORK_DIR}/files/camplayer-firstboot.sh"  "${ROOTFS_DIR}/usr/local/bin/camplayer-firstboot.sh"

# ── Install systemd service files ────────────────────────────────────────────
SYSTEMD_DIR="${ROOTFS_DIR}/etc/systemd/system"
install -m 644 "${STAGE_WORK_DIR}/files/camplayer.service"               "$SYSTEMD_DIR/"
install -m 644 "${STAGE_WORK_DIR}/files/camplayer-systemhelper.service"  "$SYSTEMD_DIR/"
install -m 644 "${STAGE_WORK_DIR}/files/camplayer-go2rtc.service"        "$SYSTEMD_DIR/"
install -m 644 "${STAGE_WORK_DIR}/files/camplayer-cec-start.service"     "$SYSTEMD_DIR/"
install -m 644 "${STAGE_WORK_DIR}/files/camplayer-cec-stop.service"      "$SYSTEMD_DIR/"
install -m 644 "${STAGE_WORK_DIR}/files/camplayer-firstboot.service"     "$SYSTEMD_DIR/"

# ── Install boot config files ─────────────────────────────────────────────────
# /boot is the FAT32 partition; during pi-gen build it is accessible as ${ROOTFS_DIR}/boot
install -m 644 "${STAGE_WORK_DIR}/files/camplayer-config.ini" "${ROOTFS_DIR}/boot/camplayer-config.ini"
install -m 644 "${STAGE_WORK_DIR}/files/system-config.ini"    "${ROOTFS_DIR}/boot/system-config.ini"

# Append to /boot/config.txt
cat "${STAGE_WORK_DIR}/files/config.txt.overlay" >> "${ROOTFS_DIR}/boot/config.txt"

# ── Install MOTD / issue ──────────────────────────────────────────────────────
install -m 644 "${STAGE_WORK_DIR}/files/motd"  "${ROOTFS_DIR}/etc/motd"
install -m 644 "${STAGE_WORK_DIR}/files/issue" "${ROOTFS_DIR}/etc/issue"

# ── In-chroot setup ───────────────────────────────────────────────────────────
on_chroot << EOF
set -e

# Install Python dependencies
pip3 install --break-system-packages \
  -r /usr/local/share/camplayer/systemhelper/requirements.txt 2>/dev/null || true
pip3 install --break-system-packages \
  -r /usr/local/share/camplayer/web/backend/requirements.txt 2>/dev/null || true

# Install the camplayer package itself
if [ -f /usr/local/share/camplayer/setup.py ] || [ -f /usr/local/share/camplayer/pyproject.toml ]; then
  pip3 install --break-system-packages /usr/local/share/camplayer/
fi

# Create a convenience symlink for the camplayer entrypoint
if [ -f /usr/local/share/camplayer/camplayer/__main__.py ]; then
  cat > /usr/local/bin/camplayer << 'SCRIPT'
#!/bin/bash
exec python3 -m camplayer "\$@"
SCRIPT
  chmod +x /usr/local/bin/camplayer
fi

# Enable services
systemctl enable camplayer-firstboot.service
systemctl enable camplayer-systemhelper.service
systemctl enable camplayer-go2rtc.service
systemctl enable fake-hwclock.service
systemctl enable avahi-daemon.service

# Configure auto-login on tty1 for user pi
mkdir -p /etc/systemd/system/getty@tty1.service.d
cat > /etc/systemd/system/getty@tty1.service.d/autologin.conf << 'UNIT'
[Service]
ExecStart=
ExecStart=-/sbin/agetty --autologin pi --noclear %I \$TERM
UNIT

# Set hostname
echo "camplayer" > /etc/hostname
sed -i 's/127\.0\.1\.1.*/127.0.1.1\tcamplayer/' /etc/hosts || \
  echo "127.0.1.1\tcamplayer" >> /etc/hosts

# Disable getty on tty2-6 to save RAM
for i in 2 3 4 5 6; do
  systemctl disable getty@tty\${i}.service 2>/dev/null || true
done

# Disable unneeded services
systemctl disable triggerhappy.service 2>/dev/null || true

EOF

echo "Stage 01-camplayer-install complete."
