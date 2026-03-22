#!/usr/bin/python3

import subprocess
import time
import os

from utils.logger import LOG
from utils.settings import BACKGROUND, CONFIG
from utils.constants import CONSTANTS
from utils.globals import GLOBALS


class BackGround(object):

    # Overlays in front of video
    LOADING     = "icon_loading.png"
    PAUSED      = "icon_paused.png"
    CONTROL     = "icon_control.png"

    # Backgrounds behind video
    NOLINK_1X1  = "nolink_1x1.png"
    NOLINK_2X2  = "nolink_2x2.png"
    NOLINK_3X3  = "nolink_3x3.png"
    NOLINK_4X4  = "nolink_4x4.png"
    NOLINK_1P5  = "nolink_1P5.png"
    NOLINK_1P7  = "nolink_1P7.png"
    NOLINK_1P12 = "nolink_1P12.png"
    NOLINK_2P8  = "nolink_2P8.png"
    NOLINK_3P4  = "nolink_3P4.png"

    @classmethod
    def NOLINK(cls, window_count):
        """Get NO LINK image background based on window count"""

        _map = ({
            1: cls.NOLINK_1X1,
            4: cls.NOLINK_2X2,
            6: cls.NOLINK_1P5,
            7: cls.NOLINK_3P4,
            8: cls.NOLINK_1P7,
            9: cls.NOLINK_3X3,
            10: cls.NOLINK_2P8,
            13: cls.NOLINK_1P12,
            16: cls.NOLINK_4X4
        })

        file_path = str("%s%s_%i_%i.png" % (CONSTANTS.CACHE_DIR, _map.get(window_count).split('.png')[0],
                                            CONSTANTS.VIRT_SCREEN_WIDTH, CONSTANTS.VIRT_SCREEN_HEIGHT))

        if os.path.isfile(file_path):
            return file_path

        if BackGroundManager.scale_background(
                src_path=CONSTANTS.RESOURCE_DIR_BCKGRND + _map.get(window_count), dest_path=file_path,
                dest_width=CONSTANTS.VIRT_SCREEN_WIDTH, dest_height=CONSTANTS.VIRT_SCREEN_HEIGHT):
            return file_path

        return ""


class BackGroundManager(object):

    _MODULE = "BackGroundManager"

    _proc_background    = [None for _ in range(GLOBALS.NUM_DISPLAYS)]
    _backgrounds        = [[] for _ in range(GLOBALS.NUM_DISPLAYS)]

    active_icon         = ["" for _ in range(GLOBALS.NUM_DISPLAYS)]
    active_icon_display = ["" for _ in range(GLOBALS.NUM_DISPLAYS)]
    active_background   = ["" for _ in range(GLOBALS.NUM_DISPLAYS)]

    # fbi/fim binary to use (detected once at first call)
    _fb_binary          = None
    _fb_binary_checked  = False

    @classmethod
    def _get_fb_binary(cls):
        """Detect available framebuffer image viewer (fbi or fim)."""
        if cls._fb_binary_checked:
            return cls._fb_binary
        cls._fb_binary_checked = True
        for binary in ('fbi', 'fim'):
            try:
                subprocess.check_output(['which', binary], stderr=subprocess.DEVNULL)
                cls._fb_binary = binary
                LOG.DEBUG(cls._MODULE, "Using '%s' for background display" % binary)
                return cls._fb_binary
            except Exception:
                pass
        LOG.DEBUG(cls._MODULE, "No framebuffer image viewer found (fbi/fim); backgrounds disabled")
        return None

    @classmethod
    def show_icon_instant(cls, filename, display_idx=0):
        """Show icon in front of video immediately (stub: icons not supported in fbi backend)."""
        LOG.DEBUG(cls._MODULE, "show_icon_instant: icons not supported in fbi backend")

    @classmethod
    def hide_icon_instant(cls, display_idx=0):
        """Hide icon loaded with the instant method (stub)."""
        LOG.DEBUG(cls._MODULE, "hide_icon_instant: icons not supported in fbi backend")

    @classmethod
    def add_icon(cls, filename, display_idx=0):
        """Add icon to queue (stub: icons not supported in fbi backend)."""
        LOG.DEBUG(cls._MODULE, "add_icon: icons not supported in fbi backend")

    @classmethod
    def add_background(cls, window_count=1, display_idx=0):
        """Add background to display queue."""

        display_idx = 1 if display_idx == 1 else 0

        file_path = BackGround.NOLINK(window_count=window_count)

        if not file_path:
            return

        # Already present? -> ignore
        for image in cls._backgrounds[display_idx]:
            if image == file_path:
                return

        cls._backgrounds[display_idx].append(file_path)

    @classmethod
    def load_backgrounds(cls):
        """Display background images using fbi/fim."""

        if CONFIG.BACKGROUND_MODE == BACKGROUND.OFF or not GLOBALS.SDL2_SUPPORT:
            return

        fb_bin = cls._get_fb_binary()
        if not fb_bin:
            return

        for display_idx in range(GLOBALS.NUM_DISPLAYS):

            if len(cls._backgrounds[display_idx]) <= 0:
                continue

            # Terminate any previous background process for this display
            if cls._proc_background[display_idx]:
                try:
                    cls._proc_background[display_idx].terminate()
                except Exception:
                    pass
                cls._proc_background[display_idx] = None

            # Use the first background image
            bg_file = cls._backgrounds[display_idx][0]

            if fb_bin == 'fbi':
                fb_cmd = [
                    'fbi',
                    '-d', '/dev/fb0' if display_idx == 0 else '/dev/fb1',
                    '-T', '1',
                    '-noverbose',
                    '-a',
                    '--timeout', '0',
                    bg_file,
                ]
            else:  # fim
                fb_cmd = [
                    'fim',
                    '--no-rc',
                    '-q',
                    bg_file,
                ]

            LOG.DEBUG(cls._MODULE, "Loading background for display '%i' with command '%s'" %
                      (display_idx + 1, fb_cmd))

            try:
                cls._proc_background[display_idx] = subprocess.Popen(
                    fb_cmd, shell=False,
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception as e:
                LOG.ERROR(cls._MODULE, "Failed to start background viewer: %s" % str(e))

    @classmethod
    def load_icons(cls):
        """Load icon queue (stub: icons not supported in fbi backend)."""
        LOG.DEBUG(cls._MODULE, "load_icons: icons not supported in fbi backend")

    @classmethod
    def show_icon(cls, filename, display_idx=0):
        """Show icon (stub: icons not supported in fbi backend)."""
        cls.active_icon[1 if display_idx == 1 else 0] = filename

    @classmethod
    def hide_icon(cls, display_idx=0):
        """Hide active icon (stub: icons not supported in fbi backend)."""
        cls.active_icon[1 if display_idx == 1 else 0] = ""

    @classmethod
    def show_background(cls, filename, display_idx=0):
        """Show background from queue (dynamic mode)."""

        if CONFIG.BACKGROUND_MODE != BACKGROUND.DYNAMIC or not GLOBALS.SDL2_SUPPORT:
            return

        display_idx = 1 if display_idx == 1 else 0

        if cls.active_background[display_idx] == filename:
            return

        fb_bin = cls._get_fb_binary()
        if not fb_bin:
            return

        # Terminate existing background and start new one
        if cls._proc_background[display_idx]:
            try:
                cls._proc_background[display_idx].terminate()
            except Exception:
                pass
            cls._proc_background[display_idx] = None

        if fb_bin == 'fbi':
            fb_cmd = [
                'fbi',
                '-d', '/dev/fb0' if display_idx == 0 else '/dev/fb1',
                '-T', '1',
                '-noverbose',
                '-a',
                '--timeout', '0',
                filename,
            ]
        else:  # fim
            fb_cmd = [
                'fim',
                '--no-rc',
                '-q',
                filename,
            ]

        try:
            cls._proc_background[display_idx] = subprocess.Popen(
                fb_cmd, shell=False,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            LOG.ERROR(cls._MODULE, "Failed to start background viewer: %s" % str(e))

        cls.active_background[display_idx] = filename

    @classmethod
    def scale_background(cls, src_path, dest_path, dest_width, dest_height):
        """Scale background image to the requested width and height."""

        if not GLOBALS.FFMPEG_SUPPORT:
            return False

        ffmpeg_cmd = str("ffmpeg -i '%s' -vf scale=%i:%i '%s'" % (src_path, dest_width, dest_height, dest_path))

        try:
            subprocess.check_output(ffmpeg_cmd, shell=True, stderr=subprocess.STDOUT, timeout=5)

        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            LOG.ERROR(cls._MODULE, "Scaling background image '%s' failed" % src_path)

        if os.path.isfile(dest_path):
            return True

        return False

    @classmethod
    def destroy(cls):
        """Destroy background viewer instances."""

        for display_idx in range(GLOBALS.NUM_DISPLAYS):
            if cls._proc_background[display_idx]:
                try:
                    cls._proc_background[display_idx].terminate()
                except Exception:
                    pass
                cls._proc_background[display_idx] = None
