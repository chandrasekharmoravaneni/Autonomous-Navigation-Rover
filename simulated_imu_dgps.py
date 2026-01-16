import os
import json
import matplotlib.pyplot as plt


# JSON file 
file_path = os.path.join(os.path.dirname(__file__), "swift-gnss-20251119-150907.sbp.json")

# Debug print
print("Reading:", file_path)
print("File exists?", os.path.exists(file_path))

data = []
with open(file_path, "r") as f:
    for line in f:
        try:
            data.append(json.loads(line))
        except:
            continue

print("Total messages loaded:", len(data))


# ---------------------------------------
# EXTRACT GNSS + IMU FIELDS
# ---------------------------------------

lat = []
lon = []
height = []
tow = []

vel_n = []
vel_e = []
vel_d = []

imu_acc_x = []
imu_acc_y = []
imu_acc_z = []

imu_gyr_x = []
imu_gyr_y = []
imu_gyr_z = []

imu_tow = []

for msg in data:
    msg_name = msg.get("msg_name", "")

    # POS LLH
    if msg_name == "MSG_POS_LLH":
        lat.append(msg["lat"])
        lon.append(msg["lon"])
        height.append(msg["height"])
        tow.append(msg["tow"])

    # Velocity NED
    if msg_name == "MSG_VEL_NED":
        vel_n.append(msg["n"])
        vel_e.append(msg["e"])
        vel_d.append(msg["d"])

    # IMU RAW VALUES
    if msg_name == "MSG_IMU_RAW":
        imu_tow.append(msg["tow"])
        imu_acc_x.append(msg["acc_x"])
        imu_acc_y.append(msg["acc_y"])
        imu_acc_z.append(msg["acc_z"])
        imu_gyr_x.append(msg["gyr_x"])
        imu_gyr_y.append(msg["gyr_y"])
        imu_gyr_z.append(msg["gyr_z"])


# ---------------------------------------
#           GNSS POSITION PLOT
# ---------------------------------------
plt.figure(figsize=(8,5))
plt.plot(lon, lat, marker='o', markersize=2)
plt.title("GNSS Track (Latitude vs Longitude)")
plt.xlabel("Longitude")
plt.ylabel("Latitude")
plt.grid()
plt.show()


# ---------------------------------------
#           HEIGHT PLOT
# ---------------------------------------
plt.figure(figsize=(8,4))
plt.plot(tow, height)
plt.title("Height vs TOW")
plt.xlabel("GPS Time of Week")
plt.ylabel("Height (m)")
plt.grid()
plt.show()


# ---------------------------------------
#          VELOCITY PLOTS
# ---------------------------------------
plt.figure(figsize=(8,4))
plt.plot(vel_n, label="North")
plt.plot(vel_e, label="East")
plt.plot(vel_d, label="Down")
plt.title("Velocity (N/E/D)")
plt.legend()
plt.grid()
plt.show()


# ---------------------------------------
#          IMU ACCELERATION
# ---------------------------------------
plt.figure(figsize=(8,4))
plt.plot(imu_acc_x, label="Acc X")
plt.plot(imu_acc_y, label="Acc Y")
plt.plot(imu_acc_z, label="Acc Z")
plt.title("IMU Acceleration")
plt.legend()
plt.grid()
plt.show()


# ---------------------------------------
#              IMU GYRO
# ---------------------------------------
plt.figure(figsize=(8,4))
plt.plot(imu_gyr_x, label="Gyro X")
plt.plot(imu_gyr_y, label="Gyro Y")
plt.plot(imu_gyr_z, label="Gyro Z")
plt.title("IMU Gyroscope")
plt.legend()
plt.grid()
plt.show()
