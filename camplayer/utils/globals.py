#!/usr/bin/python3


class GLOBALS(object):
    MPV_SUPPORT             = False
    SDL2_SUPPORT            = False
    FFMPEG_SUPPORT          = False
    HWDEC_METHOD            = "auto-safe"   # v4l2m2m on Pi 4/5, auto-safe elsewhere
    NUM_DISPLAYS            = 2
    PI_SOC                  = 0
    PI_MODEL                = 0
    PI_SOC_HEVC             = False
    PYTHON_VER              = (0, 0)
    USERNAME                = ""