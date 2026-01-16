import math
import matplotlib.pyplot as plt
import numpy as np

from sbp.client.drivers.network_drivers import TCPDriver
from sbp.client.framer import Framer
from sbp.navigation import MsgPosLLH

# ======================
# CONFIG
# ======================
ROVER_IP = "195.37.48.233"
PORT = 55555

# Plot window size in meters (+/-)
PLOT_RANGE = 5.0   # ← change to 2.0 for cm-level walking tests

# ======================
# HELPER: LLH → ENU (meters)
# ======================
def llh_to_enu(lat, lon, lat0, lon0):
    R = 6378137.0  # Earth radius (m)
    dlat = math.radians(lat - lat0)
    dlon = math.radians(lon - lon0)
    x = R * dlon * math.cos(math.radians(lat0))  # East
    y = R * dlat                                # North
    return x, y

# ======================
# CONNECT TO ROVER
# ======================
print("Connecting to rover...")
driver = TCPDriver(ROVER_IP, PORT)
framer = Framer(driver.read, driver.write)

print("Waiting for first GNSS fix...")

# ======================
# STATE
# ======================
lat0 = lon0 = None
xs, ys = [], []

# ======================
# MATPLOTLIB SETUP
# ======================
plt.ion()
fig, ax = plt.subplots(figsize=(8, 8))

line, = ax.plot([], [], "-b", linewidth=2)
point = ax.scatter([], [], s=60, c="red")

ax.set_xlabel("East (m)")
ax.set_ylabel("North (m)")
ax.set_title("Live DGPS / RTK Rover Track")
ax.grid(True)
ax.set_aspect("equal", adjustable="box")

# 🔒 LOCK SCALE — THIS IS THE KEY FIX
ax.set_xlim(-PLOT_RANGE, PLOT_RANGE)
ax.set_ylim(-PLOT_RANGE, PLOT_RANGE)

# ======================
# MAIN LOOP
# ======================
for msg, meta in framer:

    if isinstance(msg, MsgPosLLH):

        lat = msg.lat
        lon = msg.lon

        # Set reference on first fix
        if lat0 is None:
            lat0, lon0 = lat, lon
            print("Reference position set")
            continue

        # Convert to meters
        x, y = llh_to_enu(lat, lon, lat0, lon0)

        xs.append(x)
        ys.append(y)

        # Debug print (cm-level proof)
        print(f"E={x:.3f} m  N={y:.3f} m")

        # Update plot
        line.set_data(xs, ys)
        point.set_offsets([[x, y]])

        plt.pause(0.01)
