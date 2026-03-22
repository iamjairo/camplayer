#!/usr/bin/python3

import subprocess
import os
import time
import signal
import sys

from enum import IntEnum
from enum import unique

from utils import utils
from utils.logger import LOG
from utils.settings import CONFIG, STREAMQUALITY, AUDIOMODE
from utils.constants import CONSTANTS
from utils.globals import GLOBALS
from utils.mpvipc import MpvIPC
from streaminfo import StreamInfo


@unique
class PLAYSTATE(IntEnum):
    NONE    = 0
    INIT1   = 1     # MPV process started
    INIT2   = 2     # MPV IPC connected, stream loading
    PLAYING = 3
    BROKEN  = 4


@unique
class PLAYER(IntEnum):
    NONE    = 0
    MPV     = 1


class Window(object):

    _LOG_NAME = "Window"

    _total_weight = 0

    def __init__(self, x1, y1, x2, y2, gridindex, screen_idx, window_idx, display_idx):
        self.x1                 = x1
        self.y1                 = y1
        self.x2                 = x2
        self.y2                 = y2
        self.gridindex          = gridindex
        self._player_pid        = 0
        self._layer             = 0
        self.visible            = False
        self._forced_fullscreen = self.native_fullscreen
        self._fail_rate_hr      = 0
        self._time_playstatus   = 0
        self._time_streamstart  = 0
        self.streams            = []
        self.active_stream      = None
        self._display_name      = ""
        self._player            = PLAYER.NONE
        self.playstate          = PLAYSTATE.NONE
        self._window_num        = window_idx + 1
        self._screen_num        = screen_idx + 1
        self._display_num       = display_idx + 1
        self.force_udp          = False
        self._audio_enabled     = False

        self._ipc_ident = "D%02d_S%02d_W%02d" % (
            self._display_num, self._screen_num, self._window_num)
        self._ipc = MpvIPC(self._ipc_ident)

        LOG.DEBUG(self._LOG_NAME,
                  "init window '%s' position '%i %i %i %i' gridindex '%s'"
                  % (self._ipc_ident, x1, y1, x2, y2, str(gridindex)))

    def add_stream(self, url):
        if not url:
            return
        self.streams.append(StreamInfo(url))

    def set_display_name(self, display_name):
        if not display_name or self._display_name:
            return
        sub_file = CONSTANTS.CACHE_DIR + display_name + ".srt"
        try:
            if not os.path.isdir(os.path.dirname(sub_file)):
                os.system("mkdir -p %s" % os.path.dirname(sub_file))
            if not os.path.isfile(sub_file):
                with open(sub_file, 'w+') as file:
                    file.write('00:00:00,00 --> 99:00:00,00\n')
                    file.write(display_name + '\n')
            self._display_name = display_name
        except Exception:
            LOG.ERROR(self._LOG_NAME, "writing subtitle file failed")

    @property
    def native_fullscreen(self):
        return (self.x1 == CONSTANTS.VIRT_SCREEN_OFFSET_X and
                self.y1 == CONSTANTS.VIRT_SCREEN_OFFSET_Y and
                self.x2 == CONSTANTS.VIRT_SCREEN_OFFSET_X + CONSTANTS.VIRT_SCREEN_WIDTH and
                self.y2 == CONSTANTS.VIRT_SCREEN_OFFSET_Y + CONSTANTS.VIRT_SCREEN_HEIGHT)

    @property
    def fullscreen_mode(self):
        return self.native_fullscreen or self._forced_fullscreen

    @fullscreen_mode.setter
    def fullscreen_mode(self, value):
        self._forced_fullscreen = value

    @property
    def playtime(self):
        return time.monotonic() - self._time_streamstart

    @property
    def window_width(self):
        return int(self.x2 - self.x1)

    @property
    def window_height(self):
        return int(self.y2 - self.y1)

    def get_weight(self, stream=None):
        if stream:
            pass
        elif self.active_stream:
            stream = self.active_stream
        else:
            stream = self.get_default_stream()
        if stream:
            return stream.weight
        return 0

    def get_lowest_quality_stream(self, windowed=None):
        if len(self.streams) <= 0:
            return None
        if self.native_fullscreen:
            windowed = False
        elif windowed is None:
            windowed = not self.fullscreen_mode
        stream = None
        quality = sys.maxsize
        for strm in self.streams:
            video_valid = strm.valid_video_fullscreen if not windowed else strm.valid_video_windowed
            if quality > strm.quality > 10000 and video_valid:
                quality = strm.quality
                stream = strm
        return stream

    def get_highest_quality_stream(self, prevent_downscaling=False, windowed=None):
        if len(self.streams) <= 0:
            return None
        if self.native_fullscreen:
            windowed = False
        elif windowed is None:
            windowed = not self.fullscreen_mode
        stream = None
        window_width = CONSTANTS.VIRT_SCREEN_WIDTH if not windowed else self.window_width
        window_height = CONSTANTS.VIRT_SCREEN_HEIGHT if not windowed else self.window_height
        for strm in self.streams:
            video_valid = strm.valid_video_fullscreen if not windowed else strm.valid_video_windowed
            if strm.quality > 10000 and video_valid:
                if not stream:
                    stream = strm
                if prevent_downscaling:
                    if strm.height > stream.height and strm.height <= window_height:
                        stream = strm
                    elif strm.height < stream.height and stream.height > window_height:
                        stream = strm
                else:
                    if strm.height > stream.height and stream.height < window_height:
                        stream = strm
                    elif strm.height < stream.height and strm.height >= window_height:
                        stream = strm
        return stream

    def get_default_stream(self, windowed=None):
        if len(self.streams) <= 0:
            return None
        if self.native_fullscreen:
            windowed = False
        elif windowed is None:
            windowed = not self.fullscreen_mode
        stream = None
        if CONFIG.STREAM_QUALITY == STREAMQUALITY.LOW:
            stream = self.get_lowest_quality_stream(windowed=windowed)
        elif CONFIG.STREAM_QUALITY == STREAMQUALITY.HIGH:
            stream = self.get_highest_quality_stream(windowed=windowed)
        elif CONFIG.STREAM_QUALITY == STREAMQUALITY.AUTO:
            stream = self.get_highest_quality_stream(prevent_downscaling=True, windowed=windowed)
        return stream

    def stream_set_visible(self, _async=False, fullscreen=None):
        if self.playstate == PLAYSTATE.NONE:
            return
        if fullscreen is None:
            fullscreen = self.fullscreen_mode
        if not self.visible or (fullscreen != self.fullscreen_mode):
            LOG.INFO(self._LOG_NAME, "stream set visible '%s' '%s'"
                     % (self._ipc_ident, self.active_stream.printable_url()))
            self.fullscreen_mode = fullscreen

            # Re-open with audio state change if needed
            if CONFIG.AUDIO_MODE == AUDIOMODE.FULLSCREEN:
                if fullscreen and not self._audio_enabled and self.active_stream.has_audio:
                    self.visible = True
                    self.stream_refresh()
                    return
                if self._audio_enabled and not fullscreen:
                    self.visible = True
                    self.stream_refresh()
                    return

            # Move window into visible area by updating geometry
            if self._ipc.is_connected():
                if fullscreen:
                    self._ipc.set_geometry(
                        CONSTANTS.VIRT_SCREEN_OFFSET_X, CONSTANTS.VIRT_SCREEN_OFFSET_Y,
                        CONSTANTS.VIRT_SCREEN_OFFSET_X + CONSTANTS.VIRT_SCREEN_WIDTH,
                        CONSTANTS.VIRT_SCREEN_OFFSET_Y + CONSTANTS.VIRT_SCREEN_HEIGHT,
                        CONSTANTS.VIRT_SCREEN_WIDTH, CONSTANTS.VIRT_SCREEN_HEIGHT)
                else:
                    self._ipc.set_geometry(
                        self.x1, self.y1, self.x2, self.y2,
                        CONSTANTS.VIRT_SCREEN_WIDTH, CONSTANTS.VIRT_SCREEN_HEIGHT)
            else:
                # IPC not ready yet - restart with correct position
                self.visible = True
                self.stream_refresh()
                return

        self.visible = True

    def stream_set_invisible(self, _async=False):
        if self.playstate == PLAYSTATE.NONE:
            return
        if self.visible:
            LOG.INFO(self._LOG_NAME, "stream set invisible '%s' '%s'"
                     % (self._ipc_ident, self.active_stream.printable_url()))

            # Move window off-screen by offsetting geometry
            if self._ipc.is_connected():
                self._ipc.set_geometry(
                    self.x1 + CONSTANTS.WINDOW_OFFSET, self.y1,
                    self.x2 + CONSTANTS.WINDOW_OFFSET, self.y2,
                    CONSTANTS.VIRT_SCREEN_WIDTH, CONSTANTS.VIRT_SCREEN_HEIGHT)

            if self._audio_enabled:
                self.visible = False
                self.stream_refresh()
                return

        self.visible = False

    def get_stream_playstate(self):
        if self.playstate == PLAYSTATE.NONE:
            return self.playstate

        if self.playstate == PLAYSTATE.INIT1 and self.playtime < 1:
            return self.playstate

        old_playstate = self.playstate

        # INIT1: MPV process started, try to connect IPC socket
        if self.playstate == PLAYSTATE.INIT1:
            if self._ipc.connect(timeout=0.1):
                self.playstate = PLAYSTATE.INIT2
                LOG.DEBUG(self._LOG_NAME, "IPC connected for '%s' '%s'"
                          % (self._ipc_ident, self.active_stream.printable_url()))
            elif self.playtime > CONSTANTS.MPV_STARTUP_TIMEOUT_MS / 1000:
                self.playstate = PLAYSTATE.BROKEN

        # INIT2 / PLAYING: check actual playback status via IPC
        elif time.monotonic() > (self._time_playstatus + 10) or \
                (self.playstate == PLAYSTATE.INIT2 and time.monotonic() > (self._time_playstatus + 1)):

            LOG.DEBUG(self._LOG_NAME, "fetching playstate for '%s' '%s'"
                      % (self._ipc_ident, self.active_stream.printable_url()))

            status = self._ipc.get_playback_status()

            if status == 'playing':
                self.playstate = PLAYSTATE.PLAYING
            elif status == 'error' or (status == 'idle' and self.playtime > CONFIG.PLAYTIMEOUT_SEC):
                if self.playtime > CONFIG.PLAYTIMEOUT_SEC:
                    self.playstate = PLAYSTATE.BROKEN
            # 'paused' or 'idle' while still initializing: keep INIT2

            self._time_playstatus = time.monotonic()

        if old_playstate != self.playstate:
            LOG.INFO(self._LOG_NAME, "playstate '%s' for '%s' '%s'"
                     % (self.playstate.name, self._ipc_ident, self.active_stream.printable_url()))

        return self.playstate

    def stream_switch_quality_up(self, check_only=False, limit_default=True):
        if self.active_stream and self.playstate != PLAYSTATE.NONE:
            resolution = sys.maxsize
            stream = None
            if limit_default:
                default = self.get_default_stream(windowed=not self.fullscreen_mode)
                if default:
                    resolution = default.quality + 1
            for strm in self.streams:
                video_valid = strm.valid_video_fullscreen if self.fullscreen_mode else strm.valid_video_windowed
                if resolution > strm.quality > self.active_stream.quality and video_valid:
                    resolution = strm.quality
                    stream = strm
            if not stream:
                LOG.INFO(self._LOG_NAME, "highest quality stream already playing")
                return False
            if not check_only:
                self.stream_stop()
                time.sleep(0.1)
                self._stream_start(stream)
            return stream
        return False

    def stream_switch_quality_down(self, check_only=False):
        if self.active_stream and self.playstate != PLAYSTATE.NONE:
            resolution = 10000
            stream = None
            for strm in self.streams:
                video_valid = strm.valid_video_fullscreen if self.fullscreen_mode else strm.valid_video_windowed
                if resolution < strm.quality < self.active_stream.quality and video_valid:
                    resolution = strm.quality
                    stream = strm
            if not stream:
                LOG.INFO(self._LOG_NAME, "lowest quality stream already playing")
                return False
            if not check_only:
                self.stream_stop()
                time.sleep(0.1)
                self._stream_start(stream)
            return stream
        return False

    def stream_refresh(self):
        if self.playstate == PLAYSTATE.NONE:
            return
        stream = self.active_stream
        self.stream_stop()
        self._stream_start(stream=stream)

    def stream_stop(self):
        if self.playstate == PLAYSTATE.NONE:
            return
        LOG.INFO(self._LOG_NAME, "stopping stream '%s' '%s'"
                 % (self._ipc_ident, self.active_stream.printable_url()))

        # Graceful IPC quit
        if self._ipc.is_connected():
            self._ipc.quit()
            self._ipc.disconnect()

        # SIGTERM the process if still running
        if self._player_pid > 0:
            try:
                os.kill(self._player_pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            self._player_pid = 0

        # Clean up IPC socket file
        sock_path = CONSTANTS.MPV_IPC_DIR + CONSTANTS.MPV_IPC_SOCKET_PREFIX + self._ipc_ident + ".sock"
        try:
            if os.path.exists(sock_path):
                os.remove(sock_path)
        except OSError:
            pass

        if self.active_stream:
            Window._total_weight -= self.get_weight(self.active_stream)

        self.active_stream = None
        self.playstate = PLAYSTATE.NONE
        self._audio_enabled = False
        self._player = PLAYER.NONE

    def stream_start(self, visible=None, force_fullscreen=False, force_hq=False):
        if self.playstate != PLAYSTATE.NONE:
            return
        if visible is not None:
            self.visible = visible
        self.fullscreen_mode = force_fullscreen
        stream = None
        if force_hq:
            stream = self.get_highest_quality_stream()
        self._stream_start(stream=stream)

    def _stream_start(self, stream=None):
        if self.playstate != PLAYSTATE.NONE:
            return
        if len(self.streams) <= 0:
            return
        if not stream:
            stream = self.get_default_stream()
        if not stream:
            return

        win_width = CONSTANTS.VIRT_SCREEN_WIDTH if self.fullscreen_mode else self.window_width
        win_height = CONSTANTS.VIRT_SCREEN_HEIGHT if self.fullscreen_mode else self.window_height

        LOG.INFO(self._LOG_NAME,
                 "starting stream '%s' '%s' resolution '%ix%i' weight '%i' window '%ix%i'"
                 % (self._ipc_ident, stream.printable_url(), stream.width,
                    stream.height, self.get_weight(stream), win_width, win_height))

        if not stream.valid_video_windowed and not stream.valid_video_fullscreen:
            LOG.ERROR(self._LOG_NAME, "stream '%s' codec '%s' not valid for playback"
                      % (stream.printable_url(), stream.codec_name))
            return

        # Decoder weight budget check
        if Window._total_weight + self.get_weight(stream) > CONSTANTS.HW_DEC_MAX_WEIGTH and CONFIG.HARDWARE_CHECK:
            LOG.ERROR(self._LOG_NAME,
                      "decoder weight '%i' would exceed max '%i', skipping"
                      % (Window._total_weight + self.get_weight(stream), CONSTANTS.HW_DEC_MAX_WEIGTH))
            return

        Window._total_weight += self.get_weight(stream)
        self.active_stream = stream
        self._player = PLAYER.MPV

        # Determine window geometry
        if self.fullscreen_mode and self.visible:
            geom_x1, geom_y1 = CONSTANTS.VIRT_SCREEN_OFFSET_X, CONSTANTS.VIRT_SCREEN_OFFSET_Y
            geom_x2 = CONSTANTS.VIRT_SCREEN_OFFSET_X + CONSTANTS.VIRT_SCREEN_WIDTH
            geom_y2 = CONSTANTS.VIRT_SCREEN_OFFSET_Y + CONSTANTS.VIRT_SCREEN_HEIGHT
        else:
            # Offset off-screen if not visible (mirrors OMXplayer WINDOW_OFFSET trick)
            offset = 0 if self.visible else CONSTANTS.WINDOW_OFFSET
            geom_x1, geom_y1 = self.x1 + offset, self.y1
            geom_x2, geom_y2 = self.x2 + offset, self.y2

        w = geom_x2 - geom_x1
        h = geom_y2 - geom_y1
        geometry_str = "%ix%i+%i+%i" % (w, h, geom_x1, geom_y1)

        # Audio
        audio_enabled = (
            CONFIG.AUDIO_MODE == AUDIOMODE.FULLSCREEN and
            self.visible and self.fullscreen_mode and
            stream.has_audio
        )
        self._audio_enabled = audio_enabled

        sock_path = CONSTANTS.MPV_IPC_DIR + CONSTANTS.MPV_IPC_SOCKET_PREFIX + self._ipc_ident + ".sock"

        player_cmd = [
            'mpv',
            '--no-terminal',
            '--no-input-default-bindings',
            '--no-input-terminal',
            '--input-ipc-server=' + sock_path,
            '--hwdec=' + GLOBALS.HWDEC_METHOD,
            '--no-osc',
            '--no-osd-bar',
            '--geometry=' + geometry_str,
            '--keepaspect=no',              # stretch to fill (matches OMXplayer --aspect-mode stretch)
            '--network-timeout=' + str(CONFIG.PLAYTIMEOUT_SEC),
            '--demuxer-max-bytes=10MiB',
            '--video-latency-hacks=yes',    # reduce latency for live streams
        ]

        # Video output: auto-detect best backend
        if GLOBALS.MPV_SUPPORT:
            player_cmd.append('--vo=gpu')
            player_cmd.append('--gpu-context=drm')
            # Select HDMI connector for display
            drm_conn = 'HDMI-A-1' if self._display_num == 1 else 'HDMI-A-2'
            player_cmd.append('--drm-connector=' + drm_conn)

        # Transport
        if not self.force_udp and not stream.force_udp:
            player_cmd.append('--rtsp-transport=tcp')

        # Loop for local files (demo/test)
        if stream.url.startswith('file://'):
            player_cmd.append('--loop-file=yes')
        else:
            player_cmd.extend([
                '--cache=yes',
                '--demuxer-readahead-secs=' + str(CONFIG.BUFFERTIME_MS / 1000),
            ])

        # Audio settings
        if audio_enabled:
            volume_pct = max(0, min(100, CONFIG.AUDIO_VOLUME))
            player_cmd.append('--volume=' + str(volume_pct))
        else:
            player_cmd.append('--no-audio')

        # Video OSD (subtitles)
        if self._display_name and CONFIG.VIDEO_OSD:
            sub_file = CONSTANTS.CACHE_DIR + self._display_name + ".srt"
            if os.path.isfile(sub_file):
                player_cmd.extend(['--sub-file=' + sub_file, '--sub-auto=no'])

        LOG.DEBUG(self._LOG_NAME, "starting MPV '%s' with args '%s'"
                  % (self._ipc_ident, str(player_cmd)))

        # Append URL last (keep credentials out of the log above)
        player_cmd.append(stream.url)

        proc = subprocess.Popen(
            player_cmd, shell=False,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        self._player_pid = proc.pid
        self._time_streamstart = time.monotonic()
        self.playstate = PLAYSTATE.INIT1
        self._player = PLAYER.MPV

    def player_initializing(self):
        if self.playstate == PLAYSTATE.INIT1:
            return self.get_stream_playstate() == PLAYSTATE.INIT1
        return False

    def player_buffering(self):
        if self.playstate in (PLAYSTATE.INIT1, PLAYSTATE.INIT2):
            state = self.get_stream_playstate()
            return state in (PLAYSTATE.INIT1, PLAYSTATE.INIT2)
        return False

    @classmethod
    def stop_all_players(cls, sigkill=False):
        sig = '-9' if sigkill else '-15'
        try:
            subprocess.Popen(['killall', sig, 'mpv'], shell=False,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as error:
            LOG.ERROR(cls._LOG_NAME, "stop_all_players error: %s" % str(error))

    @classmethod
    def pidpool_update(cls):
        """No-op: MPV PIDs are tracked per-window instance."""
        pass
