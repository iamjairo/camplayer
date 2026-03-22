from pathlib import Path
from ruamel.yaml import YAML
from models import CamplayerConfig

GO2RTC_CONFIG_PATH = "/config/go2rtc.yaml"

_VALID_PREFIXES = ("rtsp://", "rtsps://", "rtmp://", "http://", "https://")


def get_stream_id(device_id: int, channel_num: int, quality_idx: int) -> str:
    """Return go2rtc stream ID for a given device/channel/quality (0-based idx)."""
    return f"D{device_id}_CH{channel_num}_Q{quality_idx + 1}"


def generate_go2rtc_config(
    cfg: CamplayerConfig,
    output_path: str = GO2RTC_CONFIG_PATH,
) -> dict:
    """
    Generate go2rtc.yaml from CamplayerConfig and write it to disk.

    Stream naming: D{device_id}_CH{channel_num}_Q{subchannel}
    Only includes rtsp://, rtsps://, rtmp://, http://, https:// URLs.
    Returns the generated config dict.
    """
    streams: dict[str, list[str]] = {}

    for device in cfg.devices:
        for ch_num in sorted(device.channels):
            channel = device.channels[ch_num]
            for idx, url in enumerate(channel.urls):
                if url.startswith(_VALID_PREFIXES):
                    stream_id = get_stream_id(device.id, ch_num, idx)
                    streams[stream_id] = [url]

    yaml = YAML()
    yaml.default_flow_style = False
    yaml.preserve_quotes = True
    yaml.width = 4096  # prevent line wrapping of long URLs

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    # Load existing file to preserve any extra top-level keys (e.g. webrtc, rtsp)
    existing: dict = {}
    if output.exists():
        try:
            with output.open("r", encoding="utf-8") as fh:
                existing = yaml.load(fh) or {}
        except Exception:
            existing = {}

    existing["api"] = {"listen": ":1984"}
    existing["streams"] = streams

    with output.open("w", encoding="utf-8") as fh:
        yaml.dump(existing, fh)

    return dict(existing)
