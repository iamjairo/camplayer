#!/usr/bin/python3

import subprocess
import re
import time
import os

# Only supported revisions are listed at the moment
# Non supported devices includes:
#   - Devices without ethernet/WLAN 
#   - Devices older than model 2
# Source: https://www.raspberrypi.org/documentation/hardware/raspberrypi/revision-codes/README.md
pi_revisions = {
    "9000c1" : {"model": "Zero W",      "supported": True, "dual_hdmi": False, "hevc": False},
    "a01040" : {"model": "Zero W",      "supported": True, "dual_hdmi": False, "hevc": False},
    "a01041" : {"model": "2B",          "supported": True, "dual_hdmi": False, "hevc": False},
    "a21041" : {"model": "2B",          "supported": True, "dual_hdmi": False, "hevc": False},
    "a22042" : {"model": "2B",          "supported": True, "dual_hdmi": False, "hevc": False},
    "a02082" : {"model": "3B",          "supported": True, "dual_hdmi": False, "hevc": False},
    "a32082" : {"model": "3B",          "supported": True, "dual_hdmi": False, "hevc": False},
    "a22082" : {"model": "3B",          "supported": True, "dual_hdmi": False, "hevc": False},
    "a52082" : {"model": "3B",          "supported": True, "dual_hdmi": False, "hevc": False},
    "a22083" : {"model": "3B",          "supported": True, "dual_hdmi": False, "hevc": False},
    "a020d3" : {"model": "3B+",         "supported": True, "dual_hdmi": False, "hevc": False},
    "a03111" : {"model": "4B 1GB",      "supported": True, "dual_hdmi": True,  "hevc": True},
    "b03111" : {"model": "4B 2GB",      "supported": True, "dual_hdmi": True,  "hevc": True},
    "c03111" : {"model": "4B 4GB",      "supported": True, "dual_hdmi": True,  "hevc": True},
    "b03112" : {"model": "4B 2GB",      "supported": True, "dual_hdmi": True,  "hevc": True},
    "c03112" : {"model": "4B 4GB",      "supported": True, "dual_hdmi": True,  "hevc": True},
    "d03114" : {"model": "4B 8GB",      "supported": True, "dual_hdmi": True,  "hevc": True},
    "b03114" : {"model": "4B 2GB",      "supported": True, "dual_hdmi": True,  "hevc": True},
    "c03114" : {"model": "4B 4GB",      "supported": True, "dual_hdmi": True,  "hevc": True},
    "c03130" : {"model": "Pi 400 4GB",  "supported": True, "dual_hdmi": True,  "hevc": True},
    "9020e0" : {"model": "3A+",         "supported": True, "dual_hdmi": False, "hevc": False},
    # Pi 4B additional revisions
    "d03140" : {"model": "CM4 8GB",     "supported": True, "dual_hdmi": True,  "hevc": True},
    "b03141" : {"model": "CM4 2GB",     "supported": True, "dual_hdmi": True,  "hevc": True},
    "c03141" : {"model": "CM4 4GB",     "supported": True, "dual_hdmi": True,  "hevc": True},
    "d03141" : {"model": "CM4 8GB",     "supported": True, "dual_hdmi": True,  "hevc": True},
}


def get_gpu_memory():
    """Get GPU memory allocation. Returns 2048 on unified memory systems (Pi 5+)."""
    try:
        response = subprocess.check_output(
            ['vcgencmd', 'get_mem', 'gpu'], timeout=2).decode()
        if response:
            result = re.findall(r'\d+', str(response))
            return int(result[0])
    except Exception:
        pass
    # Pi 5 uses unified memory - no split needed
    return 2048


def get_hardware_info():
    """Get hardware info (SoC, HW revision, S/N, Model name)"""

    revision = ""
    serial = ""
    soc = ""
    model = ""
    dual_hdmi = False
    hevc_decoder = False
    supported = False

    try:
        response = subprocess.check_output(
            ['cat', '/proc/cpuinfo'], timeout=2).decode().splitlines()

        for line in response:
            if "revision" in line.lower():
                revision = line.split(':')[1].strip()
            elif "serial" in line.lower():
                serial = line.split(':')[1].strip()
            elif "hardware" in line.lower():
                soc = line.split(':')[1].strip()

        if revision:
            rev_map = pi_revisions.get(revision)

            if rev_map:
                model = rev_map.get("model")
                supported = rev_map.get('supported')
                dual_hdmi = rev_map.get('dual_hdmi')
                hevc_decoder = rev_map.get('hevc')

        # New-style revision format (bit 23 set)
        if not model and revision:
            try:
                rev_int = int(revision, 16)
                if rev_int & (1 << 23):  # new-style
                    type_id = (rev_int >> 4) & 0xFF
                    mem_id = (rev_int >> 20) & 0x7
                    mem_map = {1: "1GB", 2: "2GB", 3: "4GB", 4: "8GB", 5: "16GB"}
                    ram = mem_map.get(mem_id, "")
                    if type_id == 0x17:  # Pi 5
                        model = "Pi 5 %s" % ram
                        supported = True
                        dual_hdmi = True
                        hevc_decoder = True
                    elif type_id == 0x25:  # CM5
                        model = "CM5 %s" % ram
                        supported = True
                        dual_hdmi = True
                        hevc_decoder = True
            except (ValueError, TypeError):
                pass
    except Exception:
        pass

    return {'soc': soc, 'revision': revision, 'serial': serial, 'hevc': hevc_decoder,
            'model': model, 'supported': supported, 'dual_hdmi': dual_hdmi}


def get_system_info():
    """Get a description of this operation system"""

    try:
        return str(subprocess.check_output(
            ['uname', '-a'], universal_newlines=True)).splitlines()[0]
    except Exception:
        pass

    return ""


def kill_service(service, force=False):
    """Terminate all processes with a given name"""

    try:
        subprocess.Popen(['killall', '-15', service], shell=False,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).wait(timeout=2)
    except Exception:
        pass

    if force:
        time.sleep(0.5)
        try:
            subprocess.Popen(['killall', '-9', service], shell=False,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).wait(timeout=2)
        except Exception:
            pass


def terminate_process(PID, force=False):
    """Terminate a process by its PID"""

    try:
        subprocess.Popen(['kill', '-15', str(PID)], shell=False,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).wait(timeout=2)
    except Exception:
        pass

    if force:
        time.sleep(0.5)
        try:
            subprocess.Popen(['kill', '-9', str(PID)], shell=False,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).wait(timeout=2)
        except Exception:
            pass


def get_display_mode(display=0):
    """Get display resolution. display=0 is primary HDMI."""
    res_width = 0
    res_height = 0
    framerate = 0
    device_name = ""

    # Strategy 1: Read from DRM sysfs (works on Pi 4/5 Bookworm)
    try:
        import glob
        connectors = glob.glob('/sys/class/drm/card*-HDMI-A-*/modes')
        if display < len(connectors):
            modes_path = sorted(connectors)[display]
            modes_content = open(modes_path).read().strip()
            if modes_content:
                first_mode = modes_content.split('\n')[0]  # e.g. "1920x1080"
                parts = first_mode.split('x')
                if len(parts) == 2:
                    res_width = int(parts[0])
                    res_height = int(parts[1])
                    framerate = 60  # default
    except Exception:
        pass

    # Strategy 2: fbset (fallback for framebuffer)
    if res_width == 0:
        try:
            output = subprocess.check_output(['fbset', '-s'],
                stderr=subprocess.DEVNULL, timeout=2).decode()
            match = re.search(r'geometry (\d+) (\d+)', output)
            if match:
                res_width = int(match.group(1))
                res_height = int(match.group(2))
        except Exception:
            pass

    # Strategy 3: legacy tvservice (Pi 3 / Buster compatibility)
    if res_width == 0:
        try:
            response = subprocess.check_output(
                ['tvservice', '--device', str(display + 2), '--status'],
                stderr=subprocess.STDOUT, timeout=2).decode().splitlines()[0]
            tmp = re.search(r'(DMT|CEA).*\((\d+)\)[\s*\S*]* (\d+)x(\d+).+@ (\d+)', response)
            if tmp:
                res_width = int(tmp.group(3))
                res_height = int(tmp.group(4))
                framerate = int(tmp.group(5))
        except Exception:
            pass

    return {'res_width': res_width, 'res_height': res_height,
            'framerate': framerate, 'device_name': device_name}


def get_hwdec_method():
    """Detect best hardware decode method for this platform."""
    hw_info = get_hardware_info()
    model = hw_info.get('model', '')

    # Pi 5 and Pi 4 support v4l2m2m
    if any(x in model for x in ['Pi 5', 'CM5', 'Pi 4', 'Pi 400', 'CM4']):
        # Check if v4l2m2m is available
        if os.path.exists('/dev/video10') or os.path.exists('/dev/video11'):
            return 'v4l2m2m'

    return 'auto-safe'


def os_package_installed(package):
    """Check if some linux package/application is installed"""

    try:
        subprocess.check_output(['which', package],
            stderr=subprocess.STDOUT).decode().splitlines()[0]

        return True

    except Exception:
        pass

    return False
