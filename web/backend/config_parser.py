import re
from configparser import RawConfigParser
from pathlib import Path
from models import (
    CamplayerConfig, Device, Channel, Screen,
    WindowAssignment, AdvancedConfig, Layout,
)

CONFIG_PATH_DEFAULT = "/config/camplayer-config.ini"


def parse_config(path: str = CONFIG_PATH_DEFAULT) -> CamplayerConfig:
    """Parse camplayer INI file → CamplayerConfig model."""
    cp = RawConfigParser()
    cp.read(path)

    devices: list[Device] = []
    screens: list[Screen] = []

    for section in cp.sections():
        # ── DEVICE sections ──────────────────────────────────────────────────
        m_dev = re.match(r'^DEVICE(\d+)$', section, re.IGNORECASE)
        if m_dev:
            device_id = int(m_dev.group(1))
            channel_names: dict[int, str] = {}
            channel_urls: dict[int, dict[int, str]] = {}

            for key, value in cp.items(section):
                m_name = re.match(r'^channel(\d+)_name$', key)
                if m_name:
                    channel_names[int(m_name.group(1))] = value
                    continue

                m_url = re.match(r'^channel(\d+)\.(\d+)_url$', key)
                if m_url:
                    ch_num = int(m_url.group(1))
                    sub_idx = int(m_url.group(2))
                    channel_urls.setdefault(ch_num, {})[sub_idx] = value

            channels: dict[int, Channel] = {}
            for ch_num, name in channel_names.items():
                url_map = channel_urls.get(ch_num, {})
                urls = [url_map[k] for k in sorted(url_map)]
                channels[ch_num] = Channel(name=name, urls=urls)

            devices.append(Device(id=device_id, channels=channels))
            continue

        # ── SCREEN sections ──────────────────────────────────────────────────
        m_scr = re.match(r'^SCREEN(\d+)$', section, re.IGNORECASE)
        if m_scr:
            screen_id = int(m_scr.group(1))
            display = int(cp.get(section, 'display', fallback='1'))
            layout = Layout(int(cp.get(section, 'layout', fallback='1')))
            windows: dict[int, WindowAssignment | None] = {}

            for key, value in cp.items(section):
                if key in ('display', 'layout'):
                    continue
                m_win = re.match(r'^window(\d+)$', key)
                if not m_win:
                    continue
                win_num = int(m_win.group(1))
                parts = [p.strip() for p in value.split(',')]
                if len(parts) == 2:
                    dev_m = re.search(r'\d+', parts[0])
                    ch_m = re.search(r'\d+', parts[1])
                    if dev_m and ch_m:
                        windows[win_num] = WindowAssignment(
                            device_id=int(dev_m.group()),
                            channel_num=int(ch_m.group()),
                        )
                    else:
                        windows[win_num] = None
                else:
                    windows[win_num] = None

            screens.append(Screen(
                id=screen_id,
                display=display,
                layout=layout,
                windows=windows,
            ))
            continue

    # ── ADVANCED section ─────────────────────────────────────────────────────
    advanced = AdvancedConfig()
    if cp.has_section('ADVANCED'):
        adv = cp['ADVANCED']
        advanced = AdvancedConfig(
            stream_quality=int(adv.get('stream_quality', '1')),
            changeover_type=int(adv.get('changeover_type', '1')),
            background=int(adv.get('background', '1')),
            hevc_mode=int(adv.get('hevc_mode', '1')),
            audio_mode=int(adv.get('audio_mode', '0')),
            screen_changeover_time=int(adv.get('screen_changeover_time', '0')),
        )

    devices.sort(key=lambda d: d.id)
    screens.sort(key=lambda s: s.id)

    return CamplayerConfig(devices=devices, screens=screens, advanced=advanced)


def serialize_config(cfg: CamplayerConfig, path: str = CONFIG_PATH_DEFAULT) -> None:
    """Write CamplayerConfig → camplayer INI file."""
    lines: list[str] = []

    for device in sorted(cfg.devices, key=lambda d: d.id):
        lines.append(f"[DEVICE{device.id}]")
        for ch_num in sorted(device.channels):
            channel = device.channels[ch_num]
            lines.append(f"channel{ch_num}_name = {channel.name}")
            for idx, url in enumerate(channel.urls, start=1):
                lines.append(f"channel{ch_num}.{idx}_url = {url}")
        lines.append("")

    for screen in sorted(cfg.screens, key=lambda s: s.id):
        lines.append(f"[SCREEN{screen.id}]")
        lines.append(f"display = {screen.display}")
        lines.append(f"layout = {int(screen.layout)}")
        for win_num in sorted(screen.windows):
            assignment = screen.windows[win_num]
            if assignment is not None:
                lines.append(
                    f"window{win_num} = device{assignment.device_id},"
                    f"channel{assignment.channel_num}"
                )
        lines.append("")

    lines.append("[ADVANCED]")
    adv = cfg.advanced
    lines.append(f"stream_quality = {adv.stream_quality}")
    lines.append(f"changeover_type = {adv.changeover_type}")
    lines.append(f"background = {adv.background}")
    lines.append(f"hevc_mode = {adv.hevc_mode}")
    lines.append(f"audio_mode = {adv.audio_mode}")
    lines.append(f"screen_changeover_time = {adv.screen_changeover_time}")
    lines.append("")

    Path(path).write_text("\n".join(lines), encoding="utf-8")


def get_raw_ini(path: str = CONFIG_PATH_DEFAULT) -> str:
    """Return raw INI text."""
    return Path(path).read_text(encoding="utf-8")


def set_raw_ini(text: str, path: str = CONFIG_PATH_DEFAULT) -> None:
    """Validate and write raw INI text (validates parse before writing)."""
    cp = RawConfigParser()
    cp.read_string(text)
    Path(path).write_text(text, encoding="utf-8")
