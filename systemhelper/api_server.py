import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "web", "backend"))


def create_api_app(config_path: str, go2rtc_url: str):
    """Import and return the FastAPI app from web/backend, configured via env vars."""
    os.environ["CAMPLAYER_CONFIG"] = config_path
    os.environ["GO2RTC_URL"] = go2rtc_url
    import main as backend_main  # noqa: PLC0415

    return backend_main.app
