#!/usr/bin/env python3
"""
Camplayer Systemhelper — open-source replacement for the proprietary
systemhelper binary. Runs a Textual TUI on the local terminal AND
embeds the FastAPI config API so camplayer.local works simultaneously.
"""
import asyncio
import threading
import uvicorn
from app import SystemhelperApp
from api_server import create_api_app


def run_api(config_path: str, go2rtc_url: str) -> None:
    """Run FastAPI in a background daemon thread."""
    api_app = create_api_app(config_path, go2rtc_url)
    uvicorn.run(api_app, host="0.0.0.0", port=8000, log_level="warning")


def main() -> None:
    import os

    config_path = os.getenv("CAMPLAYER_CONFIG", "/boot/camplayer-config.ini")
    go2rtc_url = os.getenv("GO2RTC_URL", "http://localhost:1984")

    api_thread = threading.Thread(
        target=run_api, args=(config_path, go2rtc_url), daemon=True
    )
    api_thread.start()

    app = SystemhelperApp(config_path=config_path)
    app.run()


if __name__ == "__main__":
    main()
