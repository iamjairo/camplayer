#!/bin/bash

if [ `whoami` != root ]; then
 echo "Please run with sudo"
 exit 1
fi

WORKDIR="$(dirname "$0")"
cd $WORKDIR

DESTPATH_APPDATA="/usr/local/share/camplayer/"
DESTPATH_BIN="/usr/local/bin/camplayer"
SYSTEMD_PATH="/lib/systemd/system/"

echo "Copy application files"
mkdir -p $DESTPATH_APPDATA
cp -v -R  * $DESTPATH_APPDATA
chmod 755 -R $DESTPATH_APPDATA

echo "Copy executable"
cp -v ./bin/camplayer $DESTPATH_BIN
chmod 755 $DESTPATH_BIN

echo "Installing required system packages"
apt-get update

# mpv replaces omxplayer
if ! command -v mpv &>/dev/null; then
    apt-get -y install mpv
fi

# ffmpeg/ffprobe for stream analysis and background scaling
if ! command -v ffprobe &>/dev/null; then
    apt-get -y install ffmpeg
fi

# fbi for background image display (framebuffer)
if ! command -v fbi &>/dev/null; then
    apt-get -y install fbi
fi

# v4l2 utilities for hardware decode detection
if ! dpkg -l v4l-utils &>/dev/null; then
    apt-get -y install v4l-utils
fi

# Python 3.11 is default on Bookworm
if ! command -v python3 &>/dev/null; then
    apt-get -y install python3
fi

if ! command -v pip3 &>/dev/null; then
    apt-get -y install python3-pip
fi

echo "Installing required Python packages"
pip3 show evdev 1>/dev/null 2>&1
if [ $? != 0 ]; then
    pip3 install evdev --break-system-packages 2>/dev/null || pip3 install evdev
fi

echo "Installing systemd service"
cp -v camplayer.service $SYSTEMD_PATH
systemctl daemon-reload
systemctl disable camplayer.service

echo "Done! Run 'sudo systemctl enable camplayer.service' to enable autostart."
