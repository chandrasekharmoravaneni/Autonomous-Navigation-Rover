import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# ---------------- Load data ----------------
df = pd.read_csv("positions_spp_speed3.csv")

# ---------------- Convert lat/lon → local meters ----------------
lat0 = np.deg2rad(df.lat_deg.mean())
lon0 = np.deg2rad(df.lon_deg.mean())
R = 6378137.0

x = R * (np.deg2rad(df.lon_deg) - lon0) * np.cos(lat0)
y = R * (np.deg2rad(df.lat_deg) - lat0)

# ---------------- Plot track ----------------
plt.figure()
plt.plot(x, y, ".", markersize=3)
plt.axis("equal")
plt.grid(True)
plt.xlabel("East (m)")
plt.ylabel("North (m)")
plt.title("SBAS Short Square-Path Trajectory")
plt.show()

# ---------------- Precision metrics ----------------
# 2D RMS precision (repeatability)
rms_2d = np.sqrt(np.mean((x - x.mean())**2 + (y - y.mean())**2))
print(f"SBAS 2D RMS precision: {rms_2d:.2f} m")

# Cross-track scatter (for straight-line test)
cross_track_std = np.std(x)
print(f"SBAS cross-track scatter: {cross_track_std:.2f} m")
