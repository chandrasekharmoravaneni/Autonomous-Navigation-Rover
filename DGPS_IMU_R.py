#!/usr/bin/env python3
"""
Improved SBP logger with IMU auto-calibration.

Save as logger_auto_cal.py and run. It will create:
  - gnss_data_base11.json
  - imu_data_base11.json

Behaviour:
  - tries to set IMU scale using IMU_AUX. If not available uses a short stationary buffer to compute scale.
  - prints calibration info and warnings to console.
"""

import json
import signal
import sys
import time
import numpy as np
from datetime import datetime

from sbp.client.drivers.network_drivers import TCPDriver
from sbp.client import Framer

# GNSS messages
from sbp.navigation import MsgPosLLH, MsgVelNED, MsgGPSTime, MsgDops, MsgBaselineNED

# IMU messages
from sbp.imu import MsgImuRaw, MsgImuAux

# System messages 
from sbp.system import MsgStartup

# -----------------------
# Output files
# -----------------------
gnss_file = open("gnss_data_base11.json", "w")
imu_file  = open("imu_data_base11.json", "w")
gnss_file.write("[\n")
imu_file.write("[\n")
first_gnss = True
first_imu  = True

# -----------------------
# Running flag
# -----------------------
running = True
def stop_handler(sig, frame):
    global running
    print("\nStopping logging (Ctrl + C)...\n")
    running = False
signal.signal(signal.SIGINT, stop_handler)

# -----------------------
# IMU calibration params
# -----------------------
GRAV = 9.80665

# initial guesses (will be replaced by auto-calibration or imu_type table)
IMU_ACC_SCALE = 9.80665 / 1000.0   # default: mg -> m/s^2 (may be wrong)
IMU_GYRO_SCALE = 1.0 / 16.4        # default guess (LSB -> deg/s) - adjust if know

# simple lookup table by imu_type (fill as you know from datasheets)
# keys are imu_type values as reported in IMU_AUX messages; values are dicts with scale factors
IMU_TYPE_TABLE = {
    # Example: (replace or expand based on your IMU_AUX values)
    # 0: {"acc_scale": 9.80665 / 1000.0, "gyro_scale": 1.0 / 16.4},  # mg, LSB/deg/s
    # Add known imu_type entries here if you know them
}

# Auto-calibration runtime settings
AUTO_CALIBRATE = True
N_CAL = 300              # how many raw IMU samples to gather for calibration (stationary recommended)
cal_buffer = []          # will collect raw triples (acc counts, not scaled)
acc_scale_ready = False
got_imu_type = False
imu_type_value = None

# small helper for runtime printing
def log(*args, **kwargs):
    print(*args, **kwargs, flush=True)

# -----------------------
# Connect to SBP
# -----------------------
IP   = "195.37.48.233"
PORT = 55555

log(f"Connecting to DGPS/INS at {IP}:{PORT} ...")
driver = TCPDriver(IP, PORT, timeout=5, reconnect=True)
framer = Framer(driver.read, driver.write)
log("Streaming SBP messages...\n")

# -----------------------
# Helper functions
# -----------------------
def compute_scale_from_buffer(buf):
    """Compute robust scale factor to map raw magnitudes -> GRAV (m/s^2)."""
    arr = np.asarray(buf, dtype=float)
    mags = np.linalg.norm(arr, axis=1)
    # robust mask: discard extreme outliers
    med = np.median(mags)
    mask = (mags > 0.25*med) & (mags < 5.0*med) & np.isfinite(mags)
    if np.sum(mask) < len(mags) // 2:
        med_use = np.median(mags)
    else:
        med_use = np.median(mags[mask])
    if med_use <= 0 or not np.isfinite(med_use):
        return None
    correction = GRAV / med_use
    return correction, med_use

def set_scale_from_imu_type(t):
    """If known, set global IMU scales from IMU_TYPE_TABLE and return True."""
    global IMU_ACC_SCALE, IMU_GYRO_SCALE
    if t in IMU_TYPE_TABLE:
        info = IMU_TYPE_TABLE[t]
        IMU_ACC_SCALE = info.get("acc_scale", IMU_ACC_SCALE)
        IMU_GYRO_SCALE = info.get("gyro_scale", IMU_GYRO_SCALE)
        log(f"[IMU_TYPE] Using preset scales for imu_type={t}: acc_scale={IMU_ACC_SCALE:.9g}, gyro_scale={IMU_GYRO_SCALE:.9g}")
        return True
    return False

# -----------------------
# Main loop
# -----------------------
try:
    for msg, meta in framer:
        if not running:
            break

        timestamp = datetime.utcnow().isoformat()

        # ---------- GNSS messages ----------
        if isinstance(msg, MsgPosLLH):
            data = {
                "type": "LLH",
                "time": timestamp,
                "tow": msg.tow,
                "lat": msg.lat,
                "lon": msg.lon,
                "height": msg.height
            }
            if not first_gnss: gnss_file.write(",\n")
            first_gnss = False
            json.dump(data, gnss_file)
            log("LLH:", data)
            continue

        if isinstance(msg, MsgVelNED):
            data = {
                "type": "VEL",
                "time": timestamp,
                "tow": msg.tow,
                "vel_n_mps": msg.n / 1000.0,
                "vel_e_mps": msg.e / 1000.0,
                "vel_d_mps": msg.d / 1000.0
            }
            if not first_gnss: gnss_file.write(",\n")
            first_gnss = False
            json.dump(data, gnss_file)
            log("VEL NED:", data)
            continue

        if isinstance(msg, MsgGPSTime):
            data = {
                "type": "TIME",
                "time": timestamp,
                "tow": msg.tow,
                "week": msg.wn
            }
            if not first_gnss: gnss_file.write(",\n")
            first_gnss = False
            json.dump(data, gnss_file)
            log("GPS TIME:", data)
            continue

        if isinstance(msg, MsgDops):
            data = {
                "type": "DOPS",
                "time": timestamp,
                "tow": msg.tow,
                "hdop": msg.hdop / 10.0,
                "vdop": msg.vdop / 10.0,
                "pdop": msg.pdop / 10.0
            }
            if not first_gnss: gnss_file.write(",\n")
            first_gnss = False
            json.dump(data, gnss_file)
            log("DOPS:", data)
            continue

        if isinstance(msg, MsgBaselineNED):
            data = {
                "type": "BASELINE",
                "time": timestamp,
                "tow": msg.tow,
                "baseline_n_m": msg.n / 1000.0,
                "baseline_e_m": msg.e / 1000.0,
                "baseline_d_m": msg.d / 1000.0
            }
            if not first_gnss: gnss_file.write(",\n")
            first_gnss = False
            json.dump(data, gnss_file)
            log("BASELINE NED:", data)
            continue

        # ---------- IMU AUX (provides imu_type) ----------
        if isinstance(msg, MsgImuAux):
            imu_type_value = int(msg.imu_type) if msg.imu_type is not None else None
            got_imu_type = imu_type_value is not None
            if got_imu_type:
                used = set_scale_from_imu_type(imu_type_value)
                if not used:
                    log(f"[IMU_AUX] imu_type={imu_type_value}, no preset in IMU_TYPE_TABLE; will auto-calibrate if possible.")
            data = {
                "type": "IMU_AUX",
                "time": timestamp,
                "temp_raw": msg.temp,
                "imu_type": imu_type_value
            }
            if not first_imu: imu_file.write(",\n")
            first_imu = False
            json.dump(data, imu_file)
            log("IMU AUX:", data)
            continue

        # ---------- IMU RAW ----------
        if isinstance(msg, MsgImuRaw):
            # raw values (usually integers / counts)
            raw_ax = float(msg.acc_x)
            raw_ay = float(msg.acc_y)
            raw_az = float(msg.acc_z)
            raw_gx = float(msg.gyr_x)
            raw_gy = float(msg.gyr_y)
            raw_gz = float(msg.gyr_z)

            # If we don't yet have scale from imu_type, collect calibration buffer
            if AUTO_CALIBRATE and (not acc_scale_ready) and (not got_imu_type):
                cal_buffer.append((raw_ax, raw_ay, raw_az))
                if len(cal_buffer) >= N_CAL:
                    result = compute_scale_from_buffer(cal_buffer)
                    if result is not None:
                        correction, med_raw = result
                        IMU_ACC_SCALE = IMU_ACC_SCALE * correction
                        acc_scale_ready = True
                        log(f"[AUTO-CAL] collected {len(cal_buffer)} samples -> med_raw={med_raw:.6f}, correction={correction:.6f}")
                        log(f"[AUTO-CAL] IMU_ACC_SCALE set to {IMU_ACC_SCALE:.9g}")
                    else:
                        log("[AUTO-CAL] failed to compute scale from buffer; continuing to collect.")

            # if imu_type was known and set_scale_from_imu_type executed earlier, acc_scale_ready True
            if got_imu_type and (not acc_scale_ready):
                # if imu_type preset exists, set acc_scale_ready
                if imu_type_value in IMU_TYPE_TABLE:
                    acc_scale_ready = True

            # apply scales (if not ready we still apply current guess, later file entries may be slightly wrong)
            acc_x = raw_ax * IMU_ACC_SCALE
            acc_y = raw_ay * IMU_ACC_SCALE
            acc_z = raw_az * IMU_ACC_SCALE

            gyr_x = raw_gx * IMU_GYRO_SCALE
            gyr_y = raw_gy * IMU_GYRO_SCALE
            gyr_z = raw_gz * IMU_GYRO_SCALE

            data = {
                "type": "IMU_RAW",
                "time": timestamp,
                "tow": msg.tow,
                "acc_x_mps2": acc_x,
                "acc_y_mps2": acc_y,
                "acc_z_mps2": acc_z,
                "gyr_x_dps": gyr_x,
                "gyr_y_dps": gyr_y,
                "gyr_z_dps": gyr_z,
                # internal diagnostics (optionally present)
                # "calibrated": acc_scale_ready
            }

            if not first_imu: imu_file.write(",\n")
            first_imu = False
            json.dump(data, imu_file)
            log("IMU RAW:", {"tow": msg.tow, "acc_x": acc_x, "acc_y": acc_y, "acc_z": acc_z,
                             "gyr_x": gyr_x, "gyr_y": gyr_y, "gyr_z": gyr_z,
                             "acc_scale_ready": acc_scale_ready})
            continue

except Exception as e:
    log("Exception in main loop:", e)
finally:
    # close JSON arrays and files cleanly
    try:
        gnss_file.write("\n]")
        imu_file.write("\n]")
        gnss_file.close()
        imu_file.close()
    except Exception:
        pass
    log("\nJSON saved as:\n  gnss_data_base11.json\n  imu_data_base11.json\nDone.")
