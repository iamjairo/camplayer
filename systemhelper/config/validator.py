import re
from configparser import ConfigParser
from typing import Optional


class ConfigValidator:
    """Validate camplayer-config.ini and system-config.ini before saving."""

    VALID_ROTATE = {0, 90, 180, 270}
    VALID_AUDIO = {"hdmi", "analog", "off"}
    RTSP_RE = re.compile(r"^(rtsp|rtsps|rtmp|http|https|file)://", re.IGNORECASE)

    @classmethod
    def validate_camplayer(cls, cp: ConfigParser) -> list[str]:
        """Return list of error strings (empty means valid)."""
        errors: list[str] = []

        for section in cp.sections():
            if section.upper().startswith("DEVICE"):
                for key, value in cp.items(section):
                    if key.endswith("_url") and value:
                        if not cls.RTSP_RE.match(value):
                            errors.append(
                                f"[{section}] {key}: invalid URL scheme '{value}'"
                            )
            elif section.upper().startswith("SCREEN"):
                layout_val = cp.get(section, "layout", fallback="1")
                try:
                    layout_int = int(layout_val)
                    valid_layouts = {1, 4, 6, 7, 8, 9, 10, 13, 16}
                    if layout_int not in valid_layouts:
                        errors.append(
                            f"[{section}] layout={layout_int} is not a valid layout value "
                            f"(valid: {sorted(valid_layouts)})"
                        )
                except ValueError:
                    errors.append(f"[{section}] layout must be an integer, got '{layout_val}'")

        return errors

    @classmethod
    def validate_system(cls, cp: ConfigParser) -> list[str]:
        """Return list of error strings for system-config.ini (empty means valid)."""
        errors: list[str] = []
        sec = "SYSTEM"
        if not cp.has_section(sec):
            return errors

        rotate = cp.get(sec, "display_rotate", fallback="0")
        try:
            if int(rotate) not in cls.VALID_ROTATE:
                errors.append(
                    f"display_rotate={rotate} invalid; must be one of {cls.VALID_ROTATE}"
                )
        except ValueError:
            errors.append(f"display_rotate must be an integer, got '{rotate}'")

        audio = cp.get(sec, "audio_output", fallback="hdmi")
        if audio not in cls.VALID_AUDIO:
            errors.append(
                f"audio_output='{audio}' invalid; must be one of {cls.VALID_AUDIO}"
            )

        for key in ("display_width", "display_height"):
            val = cp.get(sec, key, fallback="")
            if val:
                try:
                    v = int(val)
                    if v <= 0 or v > 8192:
                        errors.append(f"{key}={val} out of range (1–8192)")
                except ValueError:
                    errors.append(f"{key} must be an integer, got '{val}'")

        return errors
