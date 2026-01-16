import json
import signal
from datetime import datetime

from sbp.client.drivers.network_drivers import TCPDriver
from sbp.client import Framer

# GNSS messages
from sbp.navigation import MsgPosLLH, MsgVelNED, MsgGPSTime, MsgDops

# IMU messages
from sbp.imu import MsgImuRaw, MsgImuAux


running = True
def stop_handler(sig, frame):
    global running
    print("\nStopping logging...\n")
    running = False

signal.signal(signal.SIGINT, stop_handler)


# =============================
# OUTPUT JSON FILES
# =============================
gnss_file = open("gnss_clean.json", "w")
imu_file  = open("imu_clean.json", "w")

gnss_file.write("[\n")
imu_file.write("[\n")

first_gnss = True
first_imu = True


# =============================
# IMU Conversion Constants
# =============================
IMU_ACC_SCALE = 9.80665 / 1000.0     # mg → m/s²
IMU_GYRO_SCALE = 1.0 / 16.4          # gyro LSB → deg/sec


# =============================
# CONNECT TO SBP STREAM
# =============================
IP   = "195.37.48.235"
PORT = 55555

print(f"Connecting to GNSS at {IP}:{PORT} ...")
driver = TCPDriver(IP, PORT, timeout=5, reconnect=True)
framer = Framer(driver.read, driver.write)

print("Streaming GNSS + Velocity + IMU...\n")


# =============================
# MAIN LOOP
# =============================
for msg, meta in framer:

    if not running:
        break

    timestamp = datetime.utcnow().isoformat()

    # -----------------------------------
    # GNSS LLH
    # -----------------------------------
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
        print("LLH:", data)
        continue


    # -----------------------------------
    # GNSS Velocity (mm/s → m/s)
    # -----------------------------------
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
        print("VEL:", data)
        continue


    # -----------------------------------
    # GNSS Time
    # -----------------------------------
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
        print("GPS TIME:", data)
        continue


    # -----------------------------------
    # GNSS DOPs
    # -----------------------------------
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
        print("DOPS:", data)
        continue


    # -----------------------------------
    # IMU RAW
    # -----------------------------------
    if isinstance(msg, MsgImuRaw):

        data = {
            "time": timestamp,
            "tow": msg.tow,
            "acc_x_mps2": msg.acc_x * IMU_ACC_SCALE,
            "acc_y_mps2": msg.acc_y * IMU_ACC_SCALE,
            "acc_z_mps2": msg.acc_z * IMU_ACC_SCALE,
            "gyr_x_dps": msg.gyr_x * IMU_GYRO_SCALE,
            "gyr_y_dps": msg.gyr_y * IMU_GYRO_SCALE,
            "gyr_z_dps": msg.gyr_z * IMU_GYRO_SCALE
        }

        if not first_imu: imu_file.write(",\n")
        first_imu = False
        json.dump(data, imu_file)
        print("IMU RAW:", data)
        continue


    # -----------------------------------
    # IMU AUX (Temperature etc.)
    # -----------------------------------
    if isinstance(msg, MsgImuAux):
        data = {
            "time": timestamp,
            "temp_raw": msg.temp,
            "imu_type": msg.imu_type
        }

        if not first_imu: imu_file.write(",\n")
        first_imu = False
        json.dump(data, imu_file)
        print("IMU AUX:", data)
        continue


# =============================
# CLEAN EXIT
# =============================
gnss_file.write("\n]")
imu_file.write("\n]")
gnss_file.close()
imu_file.close()

print("\nSaved:")
print("  gnss_clean.json")
print("  imu_clean.json")
print("Done.\n")
