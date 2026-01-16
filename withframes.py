#!/usr/bin/env python3
"""
LiDAR Framewise Logger with Clean Angles & Units
-----------------------------------------------
✅ Normal angle values (e.g., 10°, 100°, 270°)
✅ x,y in millimeters or meters (configurable)
✅ Structured JSON per frame: frame_1, frame_2, etc.
Author: Satish's LiDAR Rover
"""

import socket
import math
import json
import matplotlib.pyplot as plt
import time
from datetime import datetime

# ----------------------------
# Configuration
# ----------------------------
LIDAR_IP = "192.168.0.1"
LIDAR_PORT = 2111  # CoLa-A port
SAVE_JSON = True
OUTPUT_FILE = "lidar_live_data_with_frames1.json"
UNIT = "mm"   # choose: "mm" or "m"

STX = b'\x02'
ETX = b'\x03'

# ----------------------------
# LiDAR Communication
# ----------------------------
def send_command(sock, cmd):
    sock.sendall(STX + cmd.encode() + ETX)

def read_frame(sock):
    """Read one complete telegram"""
    data = b""
    while True:
        chunk = sock.recv(4096)
        if not chunk:
            break
        data += chunk
        if ETX in chunk:
            break
    return data

# ----------------------------
# Parser
# ----------------------------
def parse_ascii_frame(frame):
    """Parse a CoLa-A ASCII LMDscandata telegram safely."""
    try:
        text = frame.decode("utf-8", errors="ignore")
    except Exception:
        return None

    if "LMDscandata" not in text:
        return None

    tokens = text.split()
    try:
        dist_idx = tokens.index("DIST1")
    except ValueError:
        return None

    # Safely locate start & step angle fields (search backwards)
    start_angle_raw = None
    step_angle_raw = None
    for i, tok in enumerate(tokens):
        if i > 15 and len(tok) >= 3:
            try:
                val = int(tok, 16)
                # first big value after "LMDscandata" usually start_angle
                if start_angle_raw is None and 1000000 < val < 2000000:
                    start_angle_raw = val
                elif step_angle_raw is None and val < 10000:
                    step_angle_raw = val
            except ValueError:
                continue

    # Fallback defaults if not found
    if start_angle_raw is None:
        start_angle_raw = -1350000
    if step_angle_raw is None:
        step_angle_raw = 3333

    start_angle = start_angle_raw / 10000.0
    step_angle = step_angle_raw / 10000.0

    try:
        num_points = int(tokens[dist_idx + 1], 16)
    except (ValueError, IndexError):
        return None

    available = len(tokens) - (dist_idx + 2)
    num_points = min(num_points, available)

    distances = []
    for i in range(num_points):
        try:
            val = int(tokens[dist_idx + 2 + i], 16)
            distances.append(val)
        except (ValueError, IndexError):
            distances.append(0)

    return {"start_angle": start_angle, "step_angle": step_angle, "distances": distances}

# ----------------------------
# Conversion
# ----------------------------
def polar_to_cartesian(scan):
    """Convert polar → Cartesian (x, y, angle)"""
    x, y, angles = [], [], []
    for i, r in enumerate(scan["distances"]):
        if r <= 20 or r >= 25000:
            continue
        angle_deg = scan["start_angle"] + i * scan["step_angle"]
        angle_rad = math.radians(angle_deg)
        # Convert to chosen units
        factor = 0.001 if UNIT == "m" else 1.0
        x.append(r * math.cos(angle_rad) * factor)
        y.append(r * math.sin(angle_rad) * factor)
        angles.append(round(angle_deg, 2))
    return x, y, angles

# ----------------------------
# Main loop
# ----------------------------
def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((LIDAR_IP, LIDAR_PORT))
    print(f" Connected to LiDAR at {LIDAR_IP}:{LIDAR_PORT}")

    send_command(sock, "sEN LMDscandata 1")
    print(" LiDAR streaming started... (Ctrl+C to stop)")

    if SAVE_JSON:
        f = open(OUTPUT_FILE, "w")
        f.write("{\n")

    plt.ion()
    fig, ax = plt.subplots(figsize=(7,7))
    scat = ax.scatter([], [], s=2)
    ax.set_xlim(-5 if UNIT=="m" else -5000, 5 if UNIT=="m" else 5000)
    ax.set_ylim(-5 if UNIT=="m" else -5000, 5 if UNIT=="m" else 5000)
    ax.set_title(f"Live LiDAR Scan - {UNIT.upper()} Units")
    ax.set_xlabel(f"X ({UNIT})")
    ax.set_ylabel(f"Y ({UNIT})")
    ax.axis("equal")
    plt.show()

    frame_id = 0
    first_entry = True

    try:
        while True:
            frame = read_frame(sock)
            if not frame:
                continue
            scan = parse_ascii_frame(frame)
            if not scan:
                continue

            x, y, angles = polar_to_cartesian(scan)
            if len(x) == 0:
                continue

            # Live update
            scat.set_offsets(list(zip(x, y)))
            fig.canvas.draw_idle()
            plt.pause(0.01)

            # Save per-frame
            frame_id += 1
            ts = datetime.now().isoformat()
            frame_key = f"\"frame_{frame_id}\""
            points = [
                {"timestamp": ts, "x": round(xi, 3), "y": round(yi, 3), "angle": ai}
                for xi, yi, ai in zip(x, y, angles)
            ]

            if SAVE_JSON:
                if not first_entry:
                    f.write(",\n")
                else:
                    first_entry = False
                f.write(f"  {frame_key}: ")
                f.write(json.dumps(points, indent=2))

            if frame_id % 10 == 0:
                print(f" Captured {frame_id} frames")

    except KeyboardInterrupt:
        print("\n Stopping LiDAR stream...")
        send_command(sock, "sEN LMDscandata 0")
        if SAVE_JSON:
            f.write("\n}\n")
            f.close()
        sock.close()
        print(" Disconnected.")
        print(f"Total frames captured: {frame_id}")
        print(f"Saved to: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
