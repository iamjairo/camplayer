from dataclasses import dataclass, field


@dataclass
class CameraDiscoveryResult:
    ip: str
    brand: str           # "hikvision" | "reolink" | "dahua" | "onvif" | "unknown"
    model: str = ""
    name: str = ""
    main_stream: str = ""    # rtsp:// URL for main/high stream
    sub_stream: str = ""     # rtsp:// URL for sub/low stream
    auth_required: bool = True
    username: str = "admin"
    password: str = ""
