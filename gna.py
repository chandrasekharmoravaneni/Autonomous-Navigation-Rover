import json
import matplotlib.pyplot as plt

# <-- change to your downloaded file -->
FILE = "full_combined_gnss_imu.json"

# Load JSON data
with open(FILE) as f:
    data = json.load(f)

lat = []
lon = []
height = []
tow = []

# Extract GNSS messages
for msg in data:
    if msg.get("msg_name") == "MSG_POS_LLH":
        lat.append(msg["lat"])
        lon.append(msg["lon"])
        height.append(msg["height"])
        tow.append(msg["tow"])

# ----------------------------
# GNSS Trajectory Plot (Lat vs Lon)
# ----------------------------
plt.figure(figsize=(8,8))
plt.plot(lon, lat, marker='o', markersize=3)
plt.title("GNSS Trajectory (Latitude vs Longitude)")
plt.xlabel("Longitude")
plt.ylabel("Latitude")
plt.grid(True)
plt.show()

# ----------------------------
# GNSS Height Plot
# ----------------------------
plt.figure(figsize=(10,5))
plt.plot(height)
plt.title("GNSS Altitude (Height Over Time)")
plt.xlabel("Sample Index")
plt.ylabel("Height (meters)")
plt.grid(True)
plt.show()

