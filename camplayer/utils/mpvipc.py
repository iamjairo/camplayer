#!/usr/bin/python3

import socket
import json
import threading
import time

from .logger import LOG
from .constants import CONSTANTS


class MpvIPC(object):
    """
    MPV JSON IPC client over a Unix domain socket.
    Each Window owns one MpvIPC instance.
    """

    _LOG_NAME = "MpvIPC"

    def __init__(self, ident):
        self._ident = ident
        self._sock_path = (CONSTANTS.MPV_IPC_DIR + CONSTANTS.MPV_IPC_SOCKET_PREFIX
                           + ident + ".sock")
        self._sock = None
        self._lock = threading.Lock()
        self._connected = False
        self._request_id = 0
        self._last_event = ""
        self._recv_buf = ""
        self._reader_thread = None
        self._running = False

    def connect(self, timeout=5.0):
        """Try to connect to the MPV IPC socket. Returns True on success."""
        if self._connected:
            return True

        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                sock.settimeout(1.0)
                sock.connect(self._sock_path)
                self._sock = sock
                self._connected = True
                self._running = True
                self._reader_thread = threading.Thread(
                    target=self._reader, daemon=True)
                self._reader_thread.start()
                LOG.DEBUG(self._LOG_NAME,
                          "connected to MPV IPC socket '%s'" % self._sock_path)
                return True
            except (FileNotFoundError, ConnectionRefusedError):
                time.sleep(0.05)
            except Exception as e:
                LOG.DEBUG(self._LOG_NAME, "connect error: %s" % str(e))
                time.sleep(0.05)

        return False

    def disconnect(self):
        """Disconnect from MPV IPC socket."""
        self._running = False
        self._connected = False
        if self._sock:
            try:
                self._sock.close()
            except Exception:
                pass
            self._sock = None

    def is_connected(self):
        return self._connected

    @property
    def last_event(self):
        return self._last_event

    def _send(self, command_dict):
        """Send a JSON command. Returns the request_id used, or None on failure."""
        if not self._connected or not self._sock:
            return None

        with self._lock:
            self._request_id += 1
            command_dict['request_id'] = self._request_id
            msg = json.dumps(command_dict) + '\n'
            try:
                self._sock.sendall(msg.encode('utf-8'))
            except Exception as e:
                LOG.DEBUG(self._LOG_NAME, "send error for '%s': %s" % (self._ident, str(e)))
                self._connected = False
                return None
            return self._request_id

    def _reader(self):
        """Background thread: drain socket, parse JSON lines, track events."""
        buf = ""
        while self._running and self._sock:
            try:
                self._sock.settimeout(0.5)
                data = self._sock.recv(4096)
                if not data:
                    break
                buf += data.decode('utf-8', errors='replace')
                while '\n' in buf:
                    line, buf = buf.split('\n', 1)
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        msg = json.loads(line)
                        if 'event' in msg:
                            self._last_event = msg['event']
                    except json.JSONDecodeError:
                        pass
            except socket.timeout:
                continue
            except Exception:
                break
        self._connected = False

    def loadfile(self, url):
        """Load and play a URL."""
        self._send({"command": ["loadfile", url, "replace"]})

    def stop(self):
        """Stop playback."""
        self._send({"command": ["stop"]})

    def quit(self):
        """Quit MPV."""
        try:
            self._send({"command": ["quit"]})
        except Exception:
            pass

    def get_property(self, name, timeout=2.0):
        """Get an MPV property value. Returns None if unavailable."""
        if not self._connected or not self._sock:
            return None
        with self._lock:
            self._request_id += 1
            req_id = self._request_id
            msg = json.dumps({"command": ["get_property", name], "request_id": req_id}) + '\n'
            try:
                self._sock.sendall(msg.encode('utf-8'))
                self._sock.settimeout(timeout)
                data = b""
                deadline = time.monotonic() + timeout
                while time.monotonic() < deadline:
                    try:
                        chunk = self._sock.recv(1024)
                        if not chunk:
                            break
                        data += chunk
                        if b'\n' in data:
                            break
                    except socket.timeout:
                        break
                self._sock.settimeout(1.0)
                for line in data.decode('utf-8', errors='replace').split('\n'):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        resp = json.loads(line)
                        if resp.get('request_id') == req_id and resp.get('error') == 'success':
                            return resp.get('data')
                    except json.JSONDecodeError:
                        pass
            except Exception as e:
                LOG.DEBUG(self._LOG_NAME, "get_property '%s' error: %s" % (name, str(e)))
        return None

    def set_property(self, name, value):
        """Set an MPV property."""
        self._send({"command": ["set_property", name, value]})

    def set_geometry(self, x1, y1, x2, y2, screen_width, screen_height):
        """
        Reposition the video window using MPV video-margin-ratio properties.
        Works with --vo=gpu and similar backends.
        """
        w = x2 - x1
        h = y2 - y1

        if w <= 0 or h <= 0:
            return

        try:
            margin_left   = x1 / screen_width
            margin_right  = (screen_width - x2) / screen_width
            margin_top    = y1 / screen_height
            margin_bottom = (screen_height - y2) / screen_height

            self._send({"command": ["set_property", "video-margin-ratio-left",   margin_left]})
            self._send({"command": ["set_property", "video-margin-ratio-right",  margin_right]})
            self._send({"command": ["set_property", "video-margin-ratio-top",    margin_top]})
            self._send({"command": ["set_property", "video-margin-ratio-bottom", margin_bottom]})
        except Exception as e:
            LOG.DEBUG(self._LOG_NAME, "set_geometry error: %s" % str(e))

    def get_playback_status(self):
        """
        Returns: 'playing', 'paused', 'idle', or 'error'
        """
        if not self._connected:
            return 'error'

        # Check last event first (fast path)
        event = self._last_event
        if event == 'end-file':
            return 'error'
        if event == 'idle':
            return 'idle'

        # Query pause state
        paused = self.get_property('pause', timeout=1.0)
        if paused is True:
            return 'paused'

        idle = self.get_property('idle-active', timeout=1.0)
        if idle is True:
            return 'idle'

        if paused is False:
            return 'playing'

        return 'idle'
