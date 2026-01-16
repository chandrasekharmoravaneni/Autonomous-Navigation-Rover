import re
import numpy as np
import matplotlib.pyplot as plt
import json
import os

# ------------------------------------------------------------
# Input / Output File Paths
# ------------------------------------------------------------
input_file = "fifth_frame_data.txt"          #  raw LiDAR telegram file
output_json = "fifth_frame_cartesian.json"   #  output JSON file

if not os.path.exists(input_file):
    raise FileNotFoundError(f" {input_file} not found! Place it beside this script.")

# ------------------------------------------------------------
# Read the raw LiDAR telegram data
# ------------------------------------------------------------
with open(input_file, "r") as f:
    telegram_text = f.read()

# Extract DIST1 block (the main distance data field)
match = re.search(r'DIST1\s+(.*?)\s+(?:RSSI1|0 0 0 0)', telegram_text, re.DOTALL)
if not match:
    raise ValueError("DIST1 block not found in the file")

# Convert hexadecimal values to integers (distance in mm)
hex_values = match.group(1).strip().split()
distances = np.array(
    [int(x, 16) for x in hex_values if re.match(r'^[0-9A-F]+$', x)],
    dtype=np.int64
)

# ------------------------------------------------------------
# Filter invalid distance values (0 or too large)
# ------------------------------------------------------------
valid_mask = (distances > 0) & (distances < 30000)
distances = distances[valid_mask]

# ------------------------------------------------------------
#  Convert to Cartesian coordinates
# ------------------------------------------------------------
# LiDAR TiM781 → ~270° Field of View
angles_deg = np.linspace(-45, 225, len(distances))
angles_rad = np.deg2rad(angles_deg)

# Polar → Cartesian
x = distances * np.cos(angles_rad)
y = distances * np.sin(angles_rad)

# ------------------------------------------------------------
# Save data as JSON
# ------------------------------------------------------------
cartesian_data = [
    {"angle_deg": float(a), "distance_mm": float(d), "x_mm": float(xx), "y_mm": float(yy)}
    for a, d, xx, yy in zip(angles_deg, distances, x, y)
]

with open(output_json, "w") as f:
    json.dump(cartesian_data, f, indent=2)

print(f"Saved {len(cartesian_data)} LiDAR points to '{output_json}'")

# ------------------------------------------------------------
#  Plot Polar and Cartesian Views
# ------------------------------------------------------------

# Polar view (distance vs angle)
plt.figure(figsize=(6,6))
ax = plt.subplot(111, polar=True)
ax.plot(angles_rad, distances, color='blue', linewidth=1)
ax.set_title("Polar range — LiDAR frame")
ax.set_theta_zero_location("E")
ax.set_theta_direction(-1)

# Cartesian top-down view
plt.figure(figsize=(6,6))
plt.scatter(x, y, s=6, color='orange')
plt.scatter(0, 0, color='black', marker='x', label='LiDAR origin')
plt.xlabel("X (mm)")
plt.ylabel("Y (mm)")
plt.title("Cartesian View — LiDAR Scan")
plt.axis("equal")
plt.grid(True)
plt.legend()
plt.show()