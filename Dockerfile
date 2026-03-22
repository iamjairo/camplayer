FROM debian:bookworm-slim

LABEL maintainer="camplayer"
LABEL description="Camplayer 2.0 - Multi IP Camera Viewer"

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    mpv \
    ffmpeg \
    fbi \
    v4l-utils \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install evdev --break-system-packages

WORKDIR /app
COPY camplayer/ /app/camplayer/
COPY resources/ /app/resources/
COPY examples/ /app/examples/
COPY bin/ /app/bin/

ENV PYTHONPATH=/app/camplayer
WORKDIR /app/camplayer

ENTRYPOINT ["python3", "camplayer.py"]
CMD ["--demo"]
