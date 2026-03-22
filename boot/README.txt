============================================================
  CAMPLAYER OS — Boot Partition Configuration
============================================================

This SD card partition (FAT32) is readable on Windows, macOS,
and Linux. You can edit the two config files below using any
plain-text editor (Notepad, TextEdit, nano, vim, etc.)

------------------------------------------------------------
  camplayer-config.ini  — Camera & layout configuration
------------------------------------------------------------

Define your IP cameras and screen layouts here.

  [DEVICE1]
  channel1_name    = friendly name shown on screen
  channel1.1_url   = rtsp://user:pass@ip/stream  (primary)
  channel1.2_url   = rtsp://user:pass@ip/stream  (fallback)

  [SCREEN1]
  layout = 1        (1=single, 4=2×2 quad, 9=3×3, etc.)
  window1 = device1,channel1

  [ADVANCED]
  stream_quality   = 1  (1=main, 2=sub)
  hevc_mode        = 1  (1=auto, 0=force H.264)
  audio_mode       = 0  (0=off, 1=on)

You can define up to 16 devices and 4 screens.

------------------------------------------------------------
  system-config.ini  — System & network configuration
------------------------------------------------------------

  hostname         = camplayer    ← mDNS: <hostname>.local
  wifi_ssid        =              ← leave blank for wired only
  wifi_password    =
  wifi_country     = US           ← 2-letter country code
  timezone         = America/New_York
  display_width    = 1920
  display_height   = 1080
  cec_enabled      = true         ← HDMI-CEC TV wake/standby

------------------------------------------------------------
  First boot
------------------------------------------------------------

1. Insert SD card, edit the files above
2. Insert SD card into your Raspberry Pi and power on
3. On first boot (~60-90 sec) the system will:
   - Apply hostname and WiFi settings
   - Download the go2rtc WebRTC relay (needs internet)
4. Access the web UI at:  http://camplayer.local
   (or http://<ip-address> if mDNS is not available)

------------------------------------------------------------
  Default credentials
------------------------------------------------------------

  SSH user:     pi
  SSH password: camplayer
  Web UI:       http://camplayer.local

Change the password after first boot:
  os_readwrite && passwd pi && os_readonly

------------------------------------------------------------
  Making persistent changes
------------------------------------------------------------

The root filesystem is READ-ONLY by default (protects SD card).
To make persistent system changes via SSH:

  os_readwrite     ← makes / writable (changes survive reboot)
  ...make changes...
  os_readonly      ← restores read-only protection

------------------------------------------------------------
  More information
------------------------------------------------------------

  GitHub:  https://github.com/raspicamplayer/camplayer
  Issues:  https://github.com/raspicamplayer/camplayer/issues
