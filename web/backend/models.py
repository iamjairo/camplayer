from pydantic import BaseModel, Field
from typing import Optional
from enum import IntEnum


class Layout(IntEnum):
    SINGLE   = 1
    GRID_2X2 = 4
    GRID_3X3 = 9
    GRID_4X4 = 16
    PIP_1P5  = 6
    PIP_1P7  = 8
    PIP_3P4  = 7
    PIP_2P8  = 10
    PIP_1P12 = 13


class Channel(BaseModel):
    name: str
    urls: list[str]  # subchannel URLs ordered by quality: [high, medium, low]


class Device(BaseModel):
    id: int  # 1-based device number
    channels: dict[int, Channel]  # channel_num → Channel


class WindowAssignment(BaseModel):
    device_id: int
    channel_num: int


class Screen(BaseModel):
    id: int  # 1-based screen number
    display: int = 1  # display index
    layout: Layout
    windows: dict[int, Optional[WindowAssignment]]  # window_num → assignment


class AdvancedConfig(BaseModel):
    stream_quality: int = 1
    changeover_type: int = 1
    background: int = 1
    hevc_mode: int = 1
    audio_mode: int = 0
    screen_changeover_time: int = 0


class CamplayerConfig(BaseModel):
    devices: list[Device]
    screens: list[Screen]
    advanced: AdvancedConfig = Field(default_factory=AdvancedConfig)


class StreamStatus(BaseModel):
    stream_id: str
    url: str
    active: bool
    consumers: int = 0
    tracks: list[str] = []


class SystemInfo(BaseModel):
    pi_model: str
    hwdec: str
    gpu_memory_mb: int
    os_version: str
    camplayer_version: str
    go2rtc_version: Optional[str]


class LayoutControlRequest(BaseModel):
    screen_index: Optional[int] = None  # for /api/layout/screen/{n}
    window_index: Optional[int] = None  # for fullscreen
