import socket
from sbp.client.drivers.network_drivers import TCPDriver
from sbp.client import Handler, Framer
from sbp.imu import SBP_MSG_IMU_RAW
import time
import numpy as np
import math

# ====== PLOTTING IMPORTS ======
import matplotlib.pyplot as plt
from collections import deque
import csv

# ==============================
# GNSS / IMU CONFIG
# ==============================
PIKSI_IP = "195.37.48.233"
PIKSI_PORT = 55555

ACC_SENSITIVITY = 16384
gravity = 9.81

# ==============================
# GLOBAL STATE (UNCHANGED)
# ==============================
time1 = None
ux = uy = uz = 0.0
distxP = distyP = distzP = 0.0

# ==============================
# LIVE PLOT BUFFERS
# ==============================
MAX_POINTS = 200
time_buf = deque(maxlen=MAX_POINTS)
distx_buf = deque(maxlen=MAX_POINTS)
disty_buf = deque(maxlen=MAX_POINTS)
distz_buf = deque(maxlen=MAX_POINTS)

# ==============================
# PLOT INITIALIZATION
# ==============================
plt.ion()
fig, ax = plt.subplots()

line_x, = ax.plot([], [], label="Dist X (m)")
line_y, = ax.plot([], [], label="Dist Y (m)")
line_z, = ax.plot([], [], label="Dist Z (m)")

ax.set_xlabel("Time (s)")
ax.set_ylabel("Distance (m)")
ax.set_title("Live IMU Distance Visualization")
ax.legend()
ax.grid(True)

# ==============================
# UTILITY FUNCTIONS (UNCHANGED)
# ==============================
def format_decimal(toformat, n):
    return math.trunc(toformat * 10**n) / (10**n)

def calculate_offsets(num_samples=10):
    accel_data = []
    with TCPDriver(PIKSI_IP, PIKSI_PORT) as driver:
        with Handler(Framer(driver.read, None)) as source:
            for i, (msg, metadata) in enumerate(source.filter(SBP_MSG_IMU_RAW)):
                if i >= num_samples:
                    break
                accel_data.append([msg.acc_x, msg.acc_y, msg.acc_z])

    accel_data = np.array(accel_data)
    offsets = np.mean(accel_data, axis=0)
    print("Accelerometer offsets:", offsets)
    return offsets

# ==============================
# MAIN IMU PROCESSING (LOGIC UNCHANGED)
# ==============================
def process_imu_data(acc_offsets):
    global time1, ux, uy, uz, distxP, distyP, distzP

    # ---- CSV FILE OPEN ----
    with open("imu_distance_log.csv", "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow([
            "time_sec",
            "dist_x_m", "dist_y_m", "dist_z_m",
            "vel_x_mps", "vel_y_mps", "vel_z_mps"
        ])

        with TCPDriver(PIKSI_IP, PIKSI_PORT) as driver:
            with Handler(Framer(driver.read, None)) as source:
                for msg, metadata in source.filter(SBP_MSG_IMU_RAW):

                    if time1 is None:
                        time1 = msg.tow
                        continue

                    time2 = msg.tow
                    dt = (time2 - time1) * 0.001
                    time1 = time2

                    accel_raw = np.array([msg.acc_x, msg.acc_y, msg.acc_z])
                    data = accel_raw - np.array(acc_offsets)

                    acc_x = (data[0] / ACC_SENSITIVITY) * gravity
                    acc_y = (data[1] / ACC_SENSITIVITY) * gravity
                    acc_z = (data[2] / ACC_SENSITIVITY) * gravity

                    arx = format_decimal(acc_x, 2)
                    ary = format_decimal(acc_y, 2)
                    arz = format_decimal(acc_z, 2)

                    if abs(arx) <= 0.1:
                        arx = 0
                    if abs(ary) <= 0.1:
                        ary = 0
                    if abs(arz) <= 0.1:
                        arz = 0

                    # Velocity integration
                    ux += arx * dt
                    uy += ary * dt
                    uz += arz * dt

                    # Distance integration
                    distxP += ux * dt
                    distyP += uy * dt
                    distzP += uz * dt

                    # ---- SAVE TO CSV ----
                    now = time.time()
                    writer.writerow([
                        now,
                        distxP, distyP, distzP,
                        ux, uy, uz
                    ])
                    csvfile.flush()

                    # ==============================
                    # LIVE PLOT UPDATE
                    # ==============================
                    time_buf.append(now)
                    distx_buf.append(distxP)
                    disty_buf.append(distyP)
                    distz_buf.append(distzP)

                    t0 = time_buf[0]
                    t_norm = [t - t0 for t in time_buf]

                    line_x.set_data(t_norm, distx_buf)
                    line_y.set_data(t_norm, disty_buf)
                    line_z.set_data(t_norm, distz_buf)

                    ax.relim()
                    ax.autoscale_view()
                    plt.pause(0.001)

                    print(
                        f"DistX={distxP:.3f}  "
                        f"DistY={distyP:.3f}  "
                        f"DistZ={distzP:.3f}"
                    )

# ==============================
# MAIN ENTRY
# ==============================
if __name__ == "__main__":
    print("Calculating accelerometer offsets...")
    acc_offsets = calculate_offsets(num_samples=10)

    print("Starting IMU processing with live visualization + CSV logging...")
    process_imu_data(acc_offsets)
    print("Processing stopped.")