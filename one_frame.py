import re
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd

file_path = "second_frame_data.txt"   # update if needed

with open(file_path, "r") as f:
    content = f.read()

# find the DIST1 token and everything after it
m = re.search(r"\bDIST1\b(.*)", content, flags=re.DOTALL | re.IGNORECASE)
if not m:
    raise ValueError("No DIST1 found in file.")

after = m.group(1).strip()

# split into tokens
tokens = after.split()

# skip first 4 header words (like 3F800000 00000000 FFFE793D D05)
if len(tokens) <= 4:
    raise ValueError("DIST1 block too short after header.")
data_tokens = tokens[4:]

# Now consume hex tokens until we hit a delimiter (non-hex token or known marker).
hex_re = re.compile(r'^[0-9A-Fa-f]+$')
stop_markers = {"RSSI1","RSSI2","DIST2","<ETX>", "<etx>", "<STX>", "<ETX>"}  # widen set if needed

dist_hex = []
for t in data_tokens:
    if t in stop_markers:
        break
    if not hex_re.match(t):
        # if token looks like e.g. '0<ETX>' or contains '<', stop
        if '<' in t or '>' in t:
            break
        # else if it's decimal number but not hex (rare), try to accept digits-only
        if not re.match(r'^\d+$', t):
            break
    dist_hex.append(t)

if not dist_hex:
    raise ValueError("No distance hex tokens found after DIST1 header.")

# convert to ints (hex -> millimeters)
distances = np.array([int(x, 16) for x in dist_hex], dtype=int)

# --- same geometry logic you used ---
num_points = len(distances)
start_angle_deg = -45      # adjust if your lidar uses different start/stop
stop_angle_deg = 225
angles_deg = np.linspace(start_angle_deg, stop_angle_deg, num_points)
angles_rad = np.deg2rad(angles_deg)

x = distances * np.cos(angles_rad)
y = distances * np.sin(angles_rad)

lidar_df = pd.DataFrame({
    "Angle (deg)": angles_deg,
    "Distance (mm)": distances,
    "X (mm)": x,
    "Y (mm)": y
})

# save csv
output_csv = "lidar_cartesian_data.csv"
lidar_df.to_csv(output_csv, index=False)
print(f"Saved {len(distances)} points to {output_csv}")

# quick plots
plt.figure(figsize=(7,7))
plt.scatter(x, y, s=3)
plt.scatter(0,0, marker='x', color='k')
plt.axis('equal')
plt.title("Cartesian LiDAR Scan")
plt.xlabel("X (mm)")
plt.ylabel("Y (mm)")
plt.grid(True)
plt.show()

plt.figure(figsize=(8,8))
ax = plt.subplot(111, polar=True)
ax.plot(angles_rad, distances, linewidth=1)
ax.set_theta_zero_location('N')
ax.set_theta_direction(-1)
ax.set_title("Polar LiDAR Scan", va='bottom')
plt.show()
