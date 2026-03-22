#!/bin/bash
# Camplayer first-boot setup
# Runs once via camplayer-firstboot.service, then disables itself

set -e
LOG="/var/log/camplayer-firstboot.log"
exec > >(tee -a "$LOG") 2>&1

echo "[$(date)] Starting Camplayer first-boot setup..."

# 1. Apply hostname from system-config.ini
HOSTNAME=$(grep -i "^hostname\s*=" /boot/system-config.ini 2>/dev/null | cut -d= -f2 | tr -d ' ' || echo "camplayer")
echo "$HOSTNAME" > /etc/hostname
hostnamectl set-hostname "$HOSTNAME" 2>/dev/null || true

# 2. Apply WiFi from system-config.ini
SSID=$(grep -i "^wifi_ssid\s*=" /boot/system-config.ini 2>/dev/null | cut -d= -f2 | tr -d ' ' || echo "")
PASS=$(grep -i "^wifi_password\s*=" /boot/system-config.ini 2>/dev/null | cut -d= -f2 | tr -d ' ' || echo "")
COUNTRY=$(grep -i "^wifi_country\s*=" /boot/system-config.ini 2>/dev/null | cut -d= -f2 | tr -d ' ' || echo "US")
if [ -n "$SSID" ]; then
  echo "[$(date)] Configuring WiFi: $SSID"
  nmcli radio wifi on 2>/dev/null || true
  nmcli dev wifi connect "$SSID" password "$PASS" 2>/dev/null || true
fi

# 3. Apply timezone
TZ=$(grep -i "^timezone\s*=" /boot/system-config.ini 2>/dev/null | cut -d= -f2 | tr -d ' ' || echo "America/New_York")
timedatectl set-timezone "$TZ" 2>/dev/null || true

# 4. Patch /boot/cmdline.txt (add quiet splash params if not already present)
CMDLINE="/boot/cmdline.txt"
if [ -f "$CMDLINE" ] && ! grep -q "splash" "$CMDLINE"; then
  sed -i 's/$/ quiet splash logo.nologo loglevel=0 vt.global_cursor_default=0/' "$CMDLINE"
  echo "[$(date)] Patched cmdline.txt with quiet/splash params."
fi

# 5. Download go2rtc binary
GO2RTC_VER="1.9.4"
ARCH=$(uname -m)
case "$ARCH" in
  aarch64) GO2RTC_ARCH="arm64" ;;
  armv7l)  GO2RTC_ARCH="arm" ;;
  x86_64)  GO2RTC_ARCH="amd64" ;;
  *)       GO2RTC_ARCH="arm64" ;;
esac
echo "[$(date)] Downloading go2rtc $GO2RTC_VER for $GO2RTC_ARCH..."
curl -fsSL "https://github.com/AlexxIT/go2rtc/releases/download/v${GO2RTC_VER}/go2rtc_linux_${GO2RTC_ARCH}" \
  -o /usr/local/bin/go2rtc && chmod +x /usr/local/bin/go2rtc
echo "[$(date)] go2rtc installed."

# 6. Generate go2rtc config from camplayer-config.ini
python3 -c "
import sys, os
sys.path.insert(0, '/usr/local/share/camplayer')
from systemhelper.api_server import create_api_app  # triggers go2rtc_sync on import
" 2>/dev/null || true

# 7. Disable this service (only runs once)
systemctl disable camplayer-firstboot.service
echo "[$(date)] First-boot setup complete."
