#!/bin/bash -e
# Install camplayer Plymouth splash theme

STAGE_WORK_DIR="$(dirname "$0")"
THEME_DIR="${ROOTFS_DIR}/usr/share/plymouth/themes/camplayer-splash"

install -d "$THEME_DIR"
install -m 644 "${STAGE_WORK_DIR}/files/camplayer-splash/camplayer-splash.plymouth" "$THEME_DIR/"
install -m 644 "${STAGE_WORK_DIR}/files/camplayer-splash/camplayer-splash.script"   "$THEME_DIR/"

on_chroot << 'EOF'
set -e
apt-get install -y --no-install-recommends plymouth plymouth-themes

# Create 1×1 black background PNG using Python (no ImageMagick dependency)
python3 - << 'PYEOF'
import struct, zlib

def chunk(name, data):
    c = name + data
    return struct.pack('>I', len(data)) + c + struct.pack('>I', zlib.crc32(c) & 0xffffffff)

sig  = b'\x89PNG\r\n\x1a\n'
ihdr = struct.pack('>IIBBBBB', 1, 1, 8, 2, 0, 0, 0)   # 1×1, 8-bit RGB
idat = zlib.compress(b'\x00\x00\x00\x00')              # filter byte + R=G=B=0
png  = sig + chunk(b'IHDR', ihdr) + chunk(b'IDAT', idat) + chunk(b'IEND', b'')

with open('/usr/share/plymouth/themes/camplayer-splash/background.png', 'wb') as f:
    f.write(png)
print("background.png created.")
PYEOF

update-alternatives --install /usr/share/plymouth/themes/default.plymouth default.plymouth \
  /usr/share/plymouth/themes/camplayer-splash/camplayer-splash.plymouth 200
update-alternatives --set default.plymouth \
  /usr/share/plymouth/themes/camplayer-splash/camplayer-splash.plymouth
update-initramfs -u || true
EOF

echo "Stage 03-plymouth-splash complete."
