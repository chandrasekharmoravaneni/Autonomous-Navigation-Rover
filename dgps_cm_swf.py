#!/usr/bin/env python3

import json, csv, math
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import cm

JSON_FNAME = "gnss_data_base2.json"
CSV_OUT = "gnss_all_llh_used.csv"
PNG_LATLON = "gnss_all_latlon_zoom.png"
PNG_COLORED = "gnss_all_track_colored_time.png"
PNG_ENU = "gnss_all_track_enu.png"

# --- load file ---
with open(JSON_FNAME, "r") as f:
    data = json.load(f)

print("Total messages in JSON:", len(data))

# --- collect ALL LLH messages in file order ---
llh_raw = []
for idx, item in enumerate(data):
    if item.get("type","").upper() == "LLH":
        # attach original file index for traceability
        entry = {
            "file_index": idx,
            "time": item.get("time"),
            "tow": item.get("tow"),
            "lat": item.get("lat"),
            "lon": item.get("lon"),
            "height": item.get("height")
        }
        llh_raw.append(entry)

print("Total LLH messages found:", len(llh_raw))

# --- detect and remove exact-zero placeholders ---
zero_mask = [(e["lat"] == 0.0 and e["lon"] == 0.0) for e in llh_raw]
n_zeros = sum(zero_mask)
print("Exact-zero LLH samples detected:", n_zeros)

# Decide: remove exact zeros (they are not real positions)
llh_used = [e for e, z in zip(llh_raw, zero_mask) if not z]
removed_indices = [e["file_index"] for e, z in zip(llh_raw, zero_mask) if z]

print("LLH used after removing zeros:", len(llh_used))
if n_zeros:
    print("Sample of removed (file indices):", removed_indices[:20])

# --- prepare arrays for plotting ---
if len(llh_used) == 0:
    raise SystemExit("No usable LLH messages after removing zeros.")

tows = np.array([e["tow"] for e in llh_used], dtype=float)
lats = np.array([e["lat"] for e in llh_used], dtype=float)
lons = np.array([e["lon"] for e in llh_used], dtype=float)
heights = np.array([e["height"] for e in llh_used], dtype=float)

# --- save CSV for inspection ---
with open(CSV_OUT, "w", newline="") as cf:
    w = csv.writer(cf)
    w.writerow(["file_index","time","tow","lat","lon","height"])
    for e in llh_used:
        w.writerow([e["file_index"], e["time"], e["tow"], e["lat"], e["lon"], e["height"]])
print("Wrote CSV:", CSV_OUT)

# --- Diagnostics ---
print(f"TOW range: {tows.min()} -> {tows.max()}  (count {len(tows)})")
print(f"Lat range: {lats.min():.12f} -> {lats.max():.12f}  Δ = {lats.max()-lats.min():.12f} deg")
print(f"Lon range: {lons.min():.12f} -> {lons.max():.12f}  Δ = {lons.max()-lons.min():.12f} deg")

# --- Plot 1: Lat vs Lon (zoomed to data) ---
pad_frac = 0.02
xmin, xmax = lons.min(), lons.max()
ymin, ymax = lats.min(), lats.max()
xpad = (xmax - xmin) * pad_frac if xmax != xmin else 1e-8
ypad = (ymax - ymin) * pad_frac if ymax != ymin else 1e-8

fig, ax = plt.subplots(figsize=(7,7))
ax.plot(lons, lats, '.-', markersize=3, linewidth=0.9)
ax.scatter(lons[0], lats[0], s=90, facecolors='none', edgecolors='green', label="start")
ax.scatter(lons[-1], lats[-1], s=90, facecolors='none', edgecolors='red', label="end")
ax.set_xlim(xmin - xpad, xmax + xpad)
ax.set_ylim(ymin - ypad, ymax + ypad)
ax.set_xlabel("Longitude (deg)")
ax.set_ylabel("Latitude (deg)")
ax.set_title("GNSS Track: Latitude vs Longitude")
ax.grid(True)
ax.legend()
plt.tight_layout()
plt.savefig(PNG_LATLON, dpi=200)
print("Saved:", PNG_LATLON)
plt.show()

# --- Plot 2: Track colored by time (direction) ---
fig, ax = plt.subplots(figsize=(7,7))
norm = plt.Normalize(vmin=tows.min(), vmax=tows.max())
cmap = cm.get_cmap("viridis")
sc = ax.scatter(lons, lats, c=tows, cmap=cmap, s=16)
ax.plot(lons, lats, '-', alpha=0.3, linewidth=0.8)
cbar = plt.colorbar(sc, ax=ax)
cbar.set_label("TOW")
ax.set_xlabel("Longitude (deg)")
ax.set_ylabel("Latitude (deg)")
ax.set_title("GNSS Track colored by TOW (direction)")
ax.set_xlim(xmin - xpad, xmax + xpad)
ax.set_ylim(ymin - ypad, ymax + ypad)
ax.grid(True)
ax.set_aspect('equal', adjustable='box')
plt.tight_layout()
plt.savefig(PNG_COLORED, dpi=200)
print("Saved:", PNG_COLORED)
plt.show()

#

print("Done. If you still see odd shapes, paste the printed ranges above and")
print("the number of zero samples detected. I can then filter / interpolate or")
print("show exactly which file indices contained zeros.") 
