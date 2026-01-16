import json
import matplotlib.pyplot as plt

FILE = "swift-gnss-20251117-143742.sbp.json"

acc_x, acc_y, acc_z = [], [], []
gyr_x, gyr_y, gyr_z = [], [], []

with open(FILE) as f:
    for line in f:
        try:
            msg = json.loads(line)
        except:
            continue

        # Read RAW IMU data
        if msg.get("msg_name") == "MSG_IMU_RAW":
            acc_x.append(msg["acc_x"])
            acc_y.append(msg["acc_y"])
            acc_z.append(msg["acc_z"])

            gyr_x.append(msg["gyr_x"])
            gyr_y.append(msg["gyr_y"])
            gyr_z.append(msg["gyr_z"])

# --------------- ACCELEROMETER PLOT --------------------
plt.figure(figsize=(12,6))
plt.plot(acc_x, label="acc_x")
plt.plot(acc_y, label="acc_y")
plt.plot(acc_z, label="acc_z")
plt.title("Hardware IMU RAW - Accelerometer")
plt.xlabel("Samples")
plt.ylabel("Raw ADC Counts")
plt.grid()
plt.legend()
plt.show()

# --------------- GYROSCOPE PLOT --------------------
plt.figure(figsize=(12,6))
plt.plot(gyr_x, label="gyr_x")
plt.plot(gyr_y, label="gyr_y")
plt.plot(gyr_z, label="gyr_z")
plt.title("Hardware IMU RAW - Gyroscope")
plt.xlabel("Samples")
plt.ylabel("Raw ADC Counts")
plt.grid()
plt.legend()
plt.show()
