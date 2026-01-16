import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

print("Script started ✅")

# ---------------- Load CSV ----------------
df = pd.read_csv("positions.csv")

print("CSV loaded ✅")
print("Columns:", df.columns.tolist())
print("Rows:", len(df))

# ---------------- Check columns ----------------
if "lat_deg" not in df.columns or "lon_deg" not in df.columns:
    raise ValueError("CSV must contain lat_deg and lon_deg columns")

# ---------------- Reference point (first sample) ----------------
lat0 = np.deg2rad(df["lat_deg"].iloc[0])
lon0 = np.deg2rad(df["lon_deg"].iloc[0])

R = 6378137.0  # Earth radius (meters)

# ---------------- Lat/Lon → local ENU ----------------
east = R * (np.deg2rad(df["lon_deg"]) - lon0) * np.cos(lat0)
north = R * (np.deg2rad(df["lat_deg"]) - lat0)

print("ENU conversion done ✅")

# ---------------- Plot ENU ----------------
plt.figure()
plt.plot(east, north, ".", markersize=2)
plt.grid(True)
plt.xlabel("East (m)")
plt.ylabel("North (m)")
plt.title("SBAS Short Straight line -Path Trajectory")
plt.axis("equal")   # preserves geometry
plt.show(block=True)

print("ENU plot shown ✅")
