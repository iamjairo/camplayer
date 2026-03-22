import os
from configparser import ConfigParser
from pathlib import Path

CAMPLAYER_CONFIG_DEFAULT = "/boot/camplayer-config.ini"
SYSTEM_CONFIG_DEFAULT = "/boot/system-config.ini"
RUNTIME_CONFIG = "/dev/shm/camplayer-config.ini"


class IniManager:
    """Thread-safe read/write of camplayer-config.ini and system-config.ini."""

    def __init__(
        self,
        camplayer_path: str = CAMPLAYER_CONFIG_DEFAULT,
        system_path: str = SYSTEM_CONFIG_DEFAULT,
    ):
        self.camplayer_path = camplayer_path
        self.system_path = system_path

    def read_camplayer(self) -> ConfigParser:
        cp = ConfigParser()
        cp.read(self.camplayer_path)
        return cp

    def write_camplayer(self, cp: ConfigParser) -> None:
        with open(self.camplayer_path, "w") as f:
            cp.write(f)
        # Also update runtime copy so camplayer service picks up the change
        runtime_dir = os.path.dirname(RUNTIME_CONFIG)
        if os.path.isdir(runtime_dir):
            with open(RUNTIME_CONFIG, "w") as f:
                cp.write(f)

    def read_system(self) -> ConfigParser:
        cp = ConfigParser()
        if os.path.exists(self.system_path):
            cp.read(self.system_path)
        return cp

    def write_system(self, cp: ConfigParser) -> None:
        with open(self.system_path, "w") as f:
            cp.write(f)

    def camplayer_exists(self) -> bool:
        return Path(self.camplayer_path).exists()

    def system_exists(self) -> bool:
        return Path(self.system_path).exists()
