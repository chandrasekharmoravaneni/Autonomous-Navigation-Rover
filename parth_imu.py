import json
import signal
import sys
import math
from datetime import datetime

from sbp.client.drivers.network_drivers import TCPDriver
from sbp.client import Framer

# GNSS messages
from sbp.navigation import MsgPosLLH, MsgVelNED, MsgGPSTime, MsgDops, MsgBaselineNED

# IMU messages
from sbp.imu import MsgImuRaw, MsgImuAux

# System messages
from sbp.system import MsgStartup


running = True


def stop_handler(sig, frame):
    global running
    print("\nStopping logging (Ctrl + C)...\n")
    running = False


signal.signal(signal.SIGINT, stop_handler)

# =============================
# OUTPUT JSON FILES
# =============================
gnss_file = open("gnss_data_base11.json", "w")
imu_file = open("imu_data_base11.json", "w")          # raw IMU
imu_ekf_file = open("imu_ekf_format.json", "w")       # EKF-style IMU

gnss_file.write("[\n")
imu_file.write("[\n")
imu_ekf_file.write("[\n")

first_gnss = True
first_imu = True
first_imu_ekf = True

# =============================
# IMU Conversion Constants
# =============================
IMU_ACC_SCALE = 9.80665 / 4096.0       # mg → m/s²
IMU_GYRO_SCALE = 1.0 / 16.4            # LSB → deg/sec

# =============================
# CONNECT TO SBP TCP STREAM
# =============================
IP = "195.37.48.233"
PORT = 55555

print(f"Connecting to DGPS/INS at {IP}:{PORT} ...")
driver = TCPDriver(IP, PORT, timeout=5, reconnect=True)
framer = Framer(driver.read, driver.write)

print("Streaming SBP messages...\n")

# =============================
# MAIN SBP LOOP
# =============================
for msg, meta in framer:

    if not running:
        break

    # Use same time for all outputs from this message
    dt = datetime.utcnow()
    timestamp_iso = dt.isoformat()
    timestamp_unix = dt.timestamp()

    # -------------------------------
    # GNSS: POS LLH
    # -------------------------------
    if isinstance(msg, MsgPosLLH):
        data = {
            "type": "LLH",
            "time": timestamp_iso,
            "tow": msg.tow,
            "lat": msg.lat,
            "lon": msg.lon,
            "height": msg.height,
        }

        if not first_gnss:
            gnss_file.write(",\n")
        first_gnss = False
        json.dump(data, gnss_file)
        print("LLH:", data, flush=True)
        continue

    # -------------------------------
    # GNSS: Velocity NED (mm/s → m/s)
    # -------------------------------
    if isinstance(msg, MsgVelNED):
        data = {
            "type": "VEL",
            "time": timestamp_iso,
            "tow": msg.tow,
            "vel_n_mps": msg.n / 1000.0,
            "vel_e_mps": msg.e / 1000.0,
            "vel_d_mps": msg.d / 1000.0,
        }

        if not first_gnss:
            gnss_file.write(",\n")
        first_gnss = False
        json.dump(data, gnss_file)
        print("VEL NED:", data, flush=True)
        continue

    # -------------------------------
    # GNSS: GPS TIME
    # -------------------------------
    if isinstance(msg, MsgGPSTime):
        data = {
            "type": "TIME",
            "time": timestamp_iso,
            "tow": msg.tow,
            "week": msg.wn,
        }

        if not first_gnss:
            gnss_file.write(",\n")
        first_gnss = False
        json.dump(data, gnss_file)
        print("GPS TIME:", data, flush=True)
        continue

    # -------------------------------
    # GNSS: DOPs
    # -------------------------------
    if isinstance(msg, MsgDops):
        data = {
            "type": "DOPS",
            "time": timestamp_iso,
            "tow": msg.tow,
            "hdop": msg.hdop / 10.0,
            "vdop": msg.vdop / 10.0,
            "pdop": msg.pdop / 10.0,
        }

        if not first_gnss:
            gnss_file.write(",\n")
        first_gnss = False
        json.dump(data, gnss_file)
        print("DOPS:", data, flush=True)
        continue

    # -------------------------------
    # GNSS: BASELINE NED (mm → m)
    # -------------------------------
    if isinstance(msg, MsgBaselineNED):
        data = {
            "type": "BASELINE",
            "time": timestamp_iso,
            "tow": msg.tow,
            "baseline_n_m": msg.n / 1000.0,
            "baseline_e_m": msg.e / 1000.0,
            "baseline_d_m": msg.d / 1000.0,
        }

        if not first_gnss:
            gnss_file.write(",\n")
        first_gnss = False
        json.dump(data, gnss_file)
        print("BASELINE NED:", data, flush=True)
        continue

    # -------------------------------
    # IMU RAW (Convert ACC, GYRO)
    # -------------------------------
    if isinstance(msg, MsgImuRaw):

        # Scale raw IMU to physical units
        acc_x = msg.acc_x * IMU_ACC_SCALE
        acc_y = msg.acc_y * IMU_ACC_SCALE
        acc_z = msg.acc_z * IMU_ACC_SCALE

        gyr_x = msg.gyr_x * IMU_GYRO_SCALE   # deg/s
        gyr_y = msg.gyr_y * IMU_GYRO_SCALE   # deg/s
        gyr_z = msg.gyr_z * IMU_GYRO_SCALE   # deg/s

        # ---------- RAW IMU JSON ----------
        data_raw = {
            "type": "IMU_RAW",
            "time": timestamp_iso,
            "tow": msg.tow,
            "acc_x_mps2": acc_x,
            "acc_y_mps2": acc_y,
            "acc_z_mps2": acc_z,
            "gyr_x_dps": gyr_x,
            "gyr_y_dps": gyr_y,
            "gyr_z_dps": gyr_z,
        }

        if not first_imu:
            imu_file.write(",\n")
        first_imu = False
        json.dump(data_raw, imu_file)
        print("IMU RAW:", data_raw, flush=True)

        # ---------- EKF-FRIENDLY IMU JSON ----------
        # gyro z from deg/s → rad/s
        yaw_rate_rad_s = gyr_z * math.pi / 180.0

        ekf_entry = {
            "timestamp": timestamp_unix,
            "angular_velocity": {
                "z": yaw_rate_rad_s,
            },
            "linear_acceleration": {
                "x": acc_x,
                "y": acc_y,
            },
        }

        if not first_imu_ekf:
            imu_ekf_file.write(",\n")
        first_imu_ekf = False
        json.dump(ekf_entry, imu_ekf_file)
        print("IMU EKF:", ekf_entry, flush=True)

        continue

    # -------------------------------
    # IMU AUX
    # -------------------------------
    if isinstance(msg, MsgImuAux):
        data = {
            "type": "IMU_AUX",
            "time": timestamp_iso,
            "temp_raw": msg.temp,
            "imu_type": msg.imu_type,
        }

        if not first_imu:
            imu_file.write(",\n")
        first_imu = False
        json.dump(data, imu_file)
        print("IMU AUX:", data, flush=True)
        continue

# ============== EXIT CLEANLY ==============
gnss_file.write("\n]")
imu_file.write("\n]")
imu_ekf_file.write("\n]")

gnss_file.close()
imu_file.close()
imu_ekf_file.close()

print("\nJSON saved as:")
print("  gnss_data_base11.json")
print("  imu_data_base11.json")
print("  imu_ekf_format.json")
print("Done.\n")
