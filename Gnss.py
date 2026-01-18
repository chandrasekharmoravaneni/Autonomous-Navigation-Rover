import json
import matplotlib.pyplot as plt
from sbp.client.drivers.file_driver import FileDriver
from sbp.client.handler import Handler
from sbp.imu import MsgImuRaw
from sbp.navigation import MsgPosLLH

SBP_FILE = "swift-gnss-20251117-142536.sbp"
JSON_OUTPUT = "converted_output.json"

# ------------------------------------------
# 1. CONVERT SBP → JSON
# ------------------------------------------

json_lines = []

driver = FileDriver(SBP_FILE)
with Handler(driver.read, None) as src:
    for msg, meta in src:
        json_lines.append(json.dumps(msg.to_json_dict()))

# Save JSON file
with open(JSON_OUTPUT, "w") as f:
    for line in json_lines:
        f.write(line + "\n")

print(f"Converted SBP → JSON saved at: {JSON_OUTPUT}")

# ------------------------------------------
# 2. PARSE JSON & EXTRACT IMU + GNSS
# ------------------------------------------

acc_x = []
acc_y = []
acc_z = []

gyr_x = []
gyr_y = []
gyr_z = []

lat_list = []
lon_list = []

with open(JSON_OUTPUT) as f:
    for line in f:
        try:
            msg = json.loads(line)
        except:
            continue

        # IMU RAW
        if msg.get("msg_type") == MsgImuRaw.msg_type:
            acc_x.append(msg["acc_x"])
            acc_y.append(msg["acc_y"])
            acc_z.append(msg["acc_z"])

            gyr_x.append(msg["gyr_x"])
            gyr_y.append(msg["gyr_y"])
            gyr_z.append(msg["gyr_z"])

        # GNSS LLH
        if msg.get("msg_type") == MsgPosLLH.msg_type:
            lat_list.append(msg["lat"])
            lon_list.append(msg["lon"])

# ------------------------------------------
# 3. PLOT IMU RAW ACC
# ------------------------------------------

plt.figure(figsize=(12,6))
plt.plot(acc_x, label="acc_x")
plt.plot(acc_y, label="acc_y")
plt.plot(acc_z, label="acc_z")
plt.title("IMU RAW Accelerometer")
plt.xlabel("Samples")
plt.ylabel("Raw ADC Counts")
plt.legend()
plt.grid()
plt.show()

# ------------------------------------------
# 4. PLOT IMU RAW GYRO
# ------------------------------------------

plt.figure(figsize=(12,6))
plt.plot(gyr_x, label="gyr_x")
plt.plot(gyr_y, label="gyr_y")
plt.plot(gyr_z, label="gyr_z")
plt.title("IMU RAW Gyroscope")
plt.xlabel("Samples")
plt.ylabel("Raw ADC Counts")
plt.legend()
plt.grid()
plt.show()

# ------------------------------------------
# 5. PLOT GNSS PATH (Latitude vs Longitude)
# ------------------------------------------

if len(lat_list) > 0:
    plt.figure(figsize=(8,8))
    plt.plot(lon_list, lat_list, marker='o', markersize=2)
    plt.title("GNSS Trajectory (Lat/Lon)")
    plt.xlabel("Longitude")
    plt.ylabel("Latitude")
    plt.grid()
    plt.show()
else:
    print("No GNSS position messages found (MSG_POS_LLH).")
