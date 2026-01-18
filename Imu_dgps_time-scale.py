import json
import numpy as np
import matplotlib.pyplot as plt

IMU_JSON = "imu_data_base12.json"   # <-- your file here

# -------------------------------
# 1. Load IMU JSON file
# -------------------------------
with open(IMU_JSON, "r") as f:
    imu = json.load(f)

# -------------------------------
# 2. Extract IMU fields
# -------------------------------
imu_tow = []
imu_ax = []
imu_ay = []
imu_az = []
imu_gx = []
imu_gy = []
imu_gz = []

for item in imu:
    if "acc_x_mps2" in item:
        imu_ax.append(item["acc_x_mps2"])
        imu_ay.append(item["acc_y_mps2"])
        imu_az.append(item["acc_z_mps2"])
        imu_gx.append(item["gyr_x_dps"])
        imu_gy.append(item["gyr_y_dps"])
        imu_gz.append(item["gyr_z_dps"])
        imu_tow.append(item.get("tow", np.nan))  # safe

# convert to numpy
imu_tow = np.array(imu_tow, dtype=float)
imu_ax = np.array(imu_ax, dtype=float)
imu_ay = np.array(imu_ay, dtype=float)
imu_az = np.array(imu_az, dtype=float)
imu_gx = np.array(imu_gx, dtype=float)
imu_gy = np.array(imu_gy, dtype=float)
imu_gz = np.array(imu_gz, dtype=float)

print("Loaded IMU samples:", len(imu_tow))

# -------------------------------
# 3. Build time axis
# -------------------------------
# If your TOW is in milliseconds, set scale = 1000
# If TOW is in seconds (Swift), scale = 1
TIME_SCALE = 1000.0

if len(imu_tow) > 0:
    t = (imu_tow - imu_tow[0]) / TIME_SCALE
else:
    t = np.arange(len(imu_ax))   # fallback: sample index

# -------------------------------
# 4. Plot Gyro vs Time
# -------------------------------
plt.figure(figsize=(10,4))
plt.plot(t, imu_gx, label="GX (deg/s)")
plt.plot(t, imu_gy, label="GY (deg/s)")
plt.plot(t, imu_gz, label="GZ (deg/s)")
plt.title("IMU Gyroscope vs Time")
plt.xlabel("Time (seconds)")
plt.ylabel("Angular rate (deg/s)")
plt.grid(True)
plt.legend()
plt.tight_layout()
plt.show()

# -------------------------------
# 5. Plot Accel vs Time
# -------------------------------
plt.figure(figsize=(10,4))
plt.plot(t, imu_ax, label="AX (m/s²)")
plt.plot(t, imu_ay, label="AY (m/s²)")
plt.plot(t, imu_az, label="AZ (m/s²)")
plt.title("IMU Accelerometer vs Time")
plt.xlabel("Time (seconds)")
plt.ylabel("Acceleration (m/s²)")
plt.grid(True)
plt.legend()
plt.tight_layout()
plt.show()
