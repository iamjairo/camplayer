"""
system-config.ini keys reverse-engineered from Camplayer OS .img analysis.
Lives on the FAT32 boot partition — user can edit by inserting SD card on any PC.
"""
from configparser import ConfigParser
from dataclasses import dataclass


@dataclass
class SystemConfig:
    # Network
    wifi_ssid: str = ""
    wifi_password: str = ""
    wifi_country: str = "US"
    hostname: str = "camplayer"

    # Display
    display_width: int = 1920
    display_height: int = 1080
    display_rotate: int = 0  # 0, 90, 180, 270

    # Timezone
    timezone: str = "America/New_York"

    # HDMI-CEC
    cec_enabled: bool = True
    cec_standby: bool = True   # Put TV to standby when camplayer stops
    cec_wakeup: bool = True    # Wake TV when camplayer starts

    # Audio
    audio_output: str = "hdmi"  # hdmi | analog | off

    # Updates
    auto_update: bool = False

    @classmethod
    def from_ini(cls, cp: ConfigParser) -> "SystemConfig":
        s = cls()
        sec = "SYSTEM"
        if not cp.has_section(sec):
            return s
        g = lambda k, fb: cp.get(sec, k, fallback=fb)
        gb = lambda k, fb: cp.getboolean(sec, k, fallback=fb)
        gi = lambda k, fb: cp.getint(sec, k, fallback=fb)
        s.wifi_ssid = g("wifi_ssid", s.wifi_ssid)
        s.wifi_password = g("wifi_password", s.wifi_password)
        s.wifi_country = g("wifi_country", s.wifi_country)
        s.hostname = g("hostname", s.hostname)
        s.display_width = gi("display_width", s.display_width)
        s.display_height = gi("display_height", s.display_height)
        s.display_rotate = gi("display_rotate", s.display_rotate)
        s.timezone = g("timezone", s.timezone)
        s.cec_enabled = gb("cec_enabled", s.cec_enabled)
        s.cec_standby = gb("cec_standby", s.cec_standby)
        s.cec_wakeup = gb("cec_wakeup", s.cec_wakeup)
        s.audio_output = g("audio_output", s.audio_output)
        s.auto_update = gb("auto_update", s.auto_update)
        return s

    def to_ini(self, cp: ConfigParser) -> None:
        sec = "SYSTEM"
        if not cp.has_section(sec):
            cp.add_section(sec)
        cp.set(sec, "wifi_ssid", self.wifi_ssid)
        cp.set(sec, "wifi_password", self.wifi_password)
        cp.set(sec, "wifi_country", self.wifi_country)
        cp.set(sec, "hostname", self.hostname)
        cp.set(sec, "display_width", str(self.display_width))
        cp.set(sec, "display_height", str(self.display_height))
        cp.set(sec, "display_rotate", str(self.display_rotate))
        cp.set(sec, "timezone", self.timezone)
        cp.set(sec, "cec_enabled", str(self.cec_enabled).lower())
        cp.set(sec, "cec_standby", str(self.cec_standby).lower())
        cp.set(sec, "cec_wakeup", str(self.cec_wakeup).lower())
        cp.set(sec, "audio_output", self.audio_output)
        cp.set(sec, "auto_update", str(self.auto_update).lower())
