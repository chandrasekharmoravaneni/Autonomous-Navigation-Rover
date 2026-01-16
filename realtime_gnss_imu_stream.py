import json
import signal
import sys
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
gnss_file = open("gnss_data_base13.json", "w")
imu_file  = open("imu_data_base13.json", "w")

gnss_file.write("[\n")
imu_file.write("[\n")

first_gnss = True
first_imu = True


# =============================
# IMU Conversion Constants
# =============================
IMU_ACC_SCALE = 9.80665 / 4096.0      # mg → m/s²
IMU_GYRO_SCALE = 1.0 / 16.4            # LSB → deg/sec


# =============================
# CONNECT TO SBP TCP STREAM
# =============================
IP   = "195.37.48.235"
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

    timestamp = datetime.utcnow().isoformat()

    # -------------------------------
    # GNSS: POS LLH
    # -------------------------------
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
        print("LLH:", data, flush=True)
        continue


    # -------------------------------
    # GNSS: Velocity NED (mm/s → m/s)
    # -------------------------------
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
        print("VEL NED:", data, flush=True)
        continue


    # -------------------------------
    # GNSS: GPS TIME
    # -------------------------------
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
        print("GPS TIME:", data, flush=True)
        continue


    # -------------------------------
    # GNSS: DOPs
    # -------------------------------
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
        print("DOPS:", data, flush=True)
        continue


    # -------------------------------
    # GNSS: BASELINE NED (mm → m)
    # -------------------------------
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
        print("BASELINE NED:", data, flush=True)
        continue


    # -------------------------------
    # IMU RAW (Convert ACC, GYRO)
    # -------------------------------
    if isinstance(msg, MsgImuRaw):

        acc_x = msg.acc_x * IMU_ACC_SCALE
        acc_y = msg.acc_y * IMU_ACC_SCALE
        acc_z = msg.acc_z * IMU_ACC_SCALE

        gyr_x = msg.gyr_x * IMU_GYRO_SCALE
        gyr_y = msg.gyr_y * IMU_GYRO_SCALE
        gyr_z = msg.gyr_z * IMU_GYRO_SCALE

        data = {
            "type": "IMU_RAW",
            "time": timestamp,
            "tow": msg.tow,
            "acc_x_mps2": acc_x,
            "acc_y_mps2": acc_y,
            "acc_z_mps2": acc_z,
            "gyr_x_dps": gyr_x,
            "gyr_y_dps": gyr_y,
            "gyr_z_dps": gyr_z
        }

        if not first_imu: imu_file.write(",\n")
        first_imu = False
        json.dump(data, imu_file)
        print("IMU RAW:", data, flush=True)
        continue


    # -------------------------------
    # IMU AUX
    # -------------------------------
    if isinstance(msg, MsgImuAux):
        data = {
            "type": "IMU_AUX",
            "time": timestamp,
            "temp_raw": msg.temp,
            "imu_type": msg.imu_type
        }

        if not first_imu: imu_file.write(",\n")
        first_imu = False
        json.dump(data, imu_file)
        print("IMU AUX:", data, flush=True)
        continue


# ============== EXIT CLEANLY ==============
gnss_file.write("\n]")
imu_file.write("\n]")
gnss_file.close()
imu_file.close()

print("\nJSON saved as:")
print("  gnss_data_base1.json")
print("  imu_data_base1.json")
print("Done.\n")
