import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Load SBAS data
sbas = pd.read_csv("positions1.csv")

# Create simulated SPP by adding noise (~2 m)
noise_m = 2.0
lat_noise = noise_m / 111111.0
lon_noise = noise_m / (111111.0 * np.cos(np.deg2rad(sbas.lat_deg.mean())))

spp = sbas.copy()
spp["lat_deg"] += np.random.normal(0, lat_noise, len(spp))
spp["lon_deg"] += np.random.normal(0, lon_noise, len(spp))

# Center for visual comparison
for df in (sbas, spp):
    df["lat_deg"] -= df["lat_deg"].mean()
    df["lon_deg"] -= df["lon_deg"].mean()

# Plot overlay
plt.figure(figsize=(7,7))
plt.plot(spp.lon_deg, spp.lat_deg, ".", markersize=3, label="SPP (simulated)")
plt.plot(sbas.lon_deg, sbas.lat_deg, ".", markersize=3, label="SBAS")
plt.xlabel("Longitude (deg)")
plt.ylabel("Latitude (deg)")
plt.title("Square Path: SPP vs SBAS")
plt.grid(True)
plt.axis("equal")
plt.legend()
plt.show()
