#!/usr/bin/env python3
"""
stream_and_log_sbp.py
- Connects to SBP TCP server (TCPDriver)
- Uses Framer to decode messages
- Logs GNSS (PosLLH, VelNED, DOP, Baseline) and IMU (ImuRaw, ImuAux)
- Writes CSV and optionally plots after you stop (Ctrl-C)
"""

import csv
import math
import signal
import sys
from collections import deque
from datetime import datetime

import matplotlib.pyplot as plt
import numpy as np

# sbp imports (from libsbp)
from sbp.client.drivers.network_drivers import TCPDriver
from sbp.client import Framer

# GNSS messages
from sbp.navigation import MsgPosLLH, MsgVelNED, MsgDops, MsgGPSTime, MsgBaselineNED
# IMU messages
from sbp.imu import MsgImuRaw, MsgImuAux
# optional system/tracking
from sbp.system import MsgStartup

# ----------------- USER SETTINGS -----------------
IP = "195.37.48.233"       # change to your device
PORT = 55555
OUT_CSV = "sbp_gnss_imu_log.csv"
IMU_ACC_SCALE = 9.80665 / 1000.0    # default: convert counts ~1mg -> m/s^2
IMU_GYRO_LSB_PER_DPS = 16.4        # default LSB per deg/s guess (adjust if known)
GNSS_UNIT_VEL = 1000.0             # velocities in logs are mm/s -> divide by 1000
GNSS_UNIT_BASELINE = 1000.0        # baseline in mm -> divide by 1000
# buffer sizes for plotting
MAX_POINTS = 2000
# -------------------------------------------------

running = True

def sigint_handler(sig, frame):
    global running
    print("\nStopping capture (SIGINT).")
    running = False

signal.signal(signal.SIGINT, sigint_handler)

# storage
gnss_rows = []      # rows to write to CSV
# use deque for quick plotting and memory control
time_q = deque(maxlen=MAX_POINTS)
lat_q = deque(maxlen=MAX_POINTS)
lon_q = deque(maxlen=MAX_POINTS)
hgt_q = deque(maxlen=MAX_POINTS)
vn_q = deque(maxlen=MAX_POINTS)
ve_q = deque(maxlen=MAX_POINTS)
vd_q = deque(maxlen=MAX_POINTS)

imu_time_q = deque(maxlen=MAX_POINTS)
ax_q = deque(maxlen=MAX_POINTS)
ay_q = deque(maxlen=MAX_POINTS)
az_q = deque(maxlen=MAX_POINTS)
gx_q = deque(maxlen=MAX_POINTS)
gy_q = deque(maxlen=MAX_POINTS)
gz_q = deque(maxlen=MAX_POINTS)

# helper to append and print minimal info
def append_gnss(ts_ms, lat, lon, hgt, vn, ve, vd, hdop):
    time_q.append((ts_ms - ts_ms0) / 1000.0 if ts_ms is not None else len(time_q))
    lat_q.append(lat)
    lon_q.append(lon)
    hgt_q.append(hgt)
    vn_q.append(vn)
    ve_q.append(ve)
    vd_q.append(vd)

# open CSV
csvfile = open(OUT_CSV, "w", newline="")
csvw = csv.writer(csvfile)
csvw.writerow([
    "utc", "tow_ms", "lat_deg", "lon_deg", "height_m",
    "vel_n_mps","vel_e_mps","vel_d_mps","hdop"
])

# create driver+framer
print(f"Connecting to {IP}:{PORT} ...")
driver = TCPDriver(IP, PORT, timeout=5, reconnect=True)   # auto reconnect
framer = Framer(driver.read, driver.write)
print("Connected. Listening for SBP messages. Ctrl-C to stop.\n")

ts_ms0 = None

# Main loop
try:
    for (msg, meta) in framer:
        if not running:
            break

        # GPS TIME (captures time-of-week in ms)
        if isinstance(msg, MsgGPSTime):
            tow = int(msg.tow)    # ms
            if ts_ms0 is None:
                ts_ms0 = tow
            # store last tow if needed by other messages via local var
            last_tow = tow
            continue

        # POS LLH
        if isinstance(msg, MsgPosLLH):
            tow = getattr(msg, "tow", None)
            # use msg fields (lat, lon, height are floats)
            lat = msg.lat
            lon = msg.lon
            hgt = msg.height
            # push placeholders for velocity (fill later if VEL arrives separately)
            append_gnss(tow, lat, lon, hgt, np.nan, np.nan, np.nan, np.nan)
            # write to CSV base row (we will overwrite velocities when available)
            csvw.writerow([
                datetime.utcnow().isoformat(), tow, lat, lon, hgt, "", "", "", ""
            ])
            csvfile.flush()
            continue

        # VEL NED (scaled integers: mm/s typically)
        if isinstance(msg, MsgVelNED):
            tow = getattr(msg, "tow", None)
            vn = float(msg.n) / GNSS_UNIT_VEL
            ve = float(msg.e) / GNSS_UNIT_VEL
            vd = float(msg.d) / GNSS_UNIT_VEL
            # append short summary to buffers (use tow if available)
            append_gnss(tow, np.nan, np.nan, np.nan, vn, ve, vd, np.nan)
            csvw.writerow([datetime.utcnow().isoformat(), tow, "", "", "", vn, ve, vd, ""])
            csvfile.flush()
            continue

        # DOPS
        if isinstance(msg, MsgDops):
            tow = getattr(msg, "tow", None)
            # DOP fields in SBP often scaled by 10
            hdop = getattr(msg, "hdop", None)
            if hdop is not None:
                try:
                    hd = float(hdop) / 10.0
                except:
                    hd = float(hdop)
            else:
                hd = np.nan
            csvw.writerow([datetime.utcnow().isoformat(), tow, "", "", "", "", "", "", hd])
            csvfile.flush()
            continue

        # BASELINE NED (RTK baseline; mm -> m)
        if isinstance(msg, MsgBaselineNED):
            tow = getattr(msg, "tow", None)
            bn = float(msg.n) / GNSS_UNIT_BASELINE
            be = float(msg.e) / GNSS_UNIT_BASELINE
            bd = float(msg.d) / GNSS_UNIT_BASELINE
            csvw.writerow([datetime.utcnow().isoformat(), tow, "", "", "", "", "", "", f"baseline_n_m:{bn} baseline_e_m:{be}"])
            csvfile.flush()
            continue

        # IMU RAW -> convert using heuristics
        if isinstance(msg, MsgImuRaw):
            tow = getattr(msg, "tow", None)
            ax_raw = msg.acc_x
            ay_raw = msg.acc_y
            az_raw = msg.acc_z
            gx_raw = msg.gyr_x
            gy_raw = msg.gyr_y
            gz_raw = msg.gyr_z

            # convert to physical units (heuristic)
            ax_m = ax_raw * IMU_ACC_SCALE
            ay_m = ay_raw * IMU_ACC_SCALE
            az_m = az_raw * IMU_ACC_SCALE

            gx_dps = gx_raw / IMU_GYRO_LSB_PER_DPS
            gy_dps = gy_raw / IMU_GYRO_LSB_PER_DPS
            gz_dps = gz_raw / IMU_GYRO_LSB_PER_DPS

            imu_time = (tow - ts_ms0) / 1000.0 if tow is not None and ts_ms0 is not None else None

            imu_time_q.append(imu_time if imu_time is not None else len(imu_time_q))
            ax_q.append(ax_m); ay_q.append(ay_m); az_q.append(az_m)
            gx_q.append(gx_dps); gy_q.append(gy_dps); gz_q.append(gz_dps)

            # also write an IMU row in CSV for post-processing (sparse mixing is okay)
            csvw.writerow([datetime.utcnow().isoformat(), tow,
                           "", "", "", "", "", "", f"IMU_ax:{ax_m:.6f},gy:{gx_dps:.3f}"])
            csvfile.flush()
            continue

        # IMU AUX (temperature / imu type) - optional
        if isinstance(msg, MsgImuAux):
            tow = getattr(msg, "tow", None)
            tmp_raw = getattr(msg, "temp", None)
            imu_type = getattr(msg, "imu_type", None)
            csvw.writerow([datetime.utcnow().isoformat(), tow, "", "", "", "", "", "", f"IMU_aux temp:{tmp_raw} type:{imu_type}"])
            csvfile.flush()
            continue

        # Startup/info messages (print minimally)
        if isinstance(msg, MsgStartup):
            print("[STARTUP] device restarted")
            continue

except Exception as e:
    print("Exception in main loop:", e)
finally:
    print("Closing CSV and driver...")
    csvfile.close()
    try:
        driver.handle.close()
    except:
        pass

# ----------------- Plotting (post-run) -----------------
print("Plotting buffered data (last samples).")

# convert deques to numpy arrays for plotting if non-empty
if len(lat_q) > 0:
    LON = np.array(lon_q, dtype=float); LAT = np.array(lat_q, dtype=float)
    plt.figure(figsize=(7,6)); plt.plot(LON, LAT, ".-", ms=3); plt.xlabel("Lon"); plt.ylabel("Lat")
    plt.title("GNSS Track (last samples)"); plt.grid(True)

if len(hgt_q) > 0:
    plt.figure(figsize=(8,3)); plt.plot(np.array(time_q), np.array(hgt_q)); plt.xlabel("s"); plt.ylabel("Height (m)")
    plt.title("Height vs time"); plt.grid(True)

if len(vn_q) > 0:
    plt.figure(figsize=(8,4)); plt.plot(np.array(time_q), np.array(vn_q), label="Vn")
    plt.plot(np.array(time_q), np.array(ve_q), label="Ve"); plt.plot(np.array(time_q), np.array(vd_q), label="Vd")
    plt.xlabel("s"); plt.ylabel("m/s"); plt.legend(); plt.title("Velocity N/E/D"); plt.grid(True)

if len(ax_q) > 0:
    plt.figure(figsize=(8,4)); plt.plot(np.array(imu_time_q), np.array(ax_q), label="ax")
    plt.plot(np.array(imu_time_q), np.array(ay_q), label="ay"); plt.plot(np.array(imu_time_q), np.array(az_q), label="az")
    plt.xlabel("s"); plt.ylabel("m/s^2"); plt.legend(); plt.title("IMU accel (converted)"); plt.grid(True)

if len(gx_q) > 0:
    plt.figure(figsize=(8,4)); plt.plot(np.array(imu_time_q), np.array(gx_q), label="gx")
    plt.plot(np.array(imu_time_q), np.array(gy_q), label="gy"); plt.plot(np.array(imu_time_q), np.array(gz_q), label="gz")
    plt.xlabel("s"); plt.ylabel("deg/s"); plt.legend(); plt.title("IMU gyro (converted)"); plt.grid(True)

plt.show()
