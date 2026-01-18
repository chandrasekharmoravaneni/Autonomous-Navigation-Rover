#!/usr/bin/env python3
"""
Live LiDAR Visualization for SICK TiM781
---------------------------------------
Connects to TiM781 (TCP CoLa-A port 2111)
Continuously receives LMDscandata telegrams
Converts polar data → Cartesian (x, y)
Displays live 2D plot of environment
Optionally saves JSON scans for logging
Includes safe parsing (no IndexError crashes)
Author: Chandra's LiDAR Rover
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
LIDAR_IP = "192.168.0.1"   # Change to your LiDAR IP
LIDAR_PORT = 2111           # CoLa-A port
SAVE_JSON = True            # Set False to disable logging
OUTPUT_FILE = "lidar_live_points.json"

STX = b'\x02'
ETX = b'\x03'

# ----------------------------
# LiDAR Communication
# ----------------------------
def send_command(sock, cmd: str):
    """Send CoLa-A framed command to LiDAR."""
    sock.sendall(STX + cmd.encode() + ETX)

def read_frame(sock):
    """Read one complete telegram between STX and ETX."""
    data = b""
    while True:
        chunk = sock.recv(4096)
        if not chunk:
            break
        data += chunk
        if ETX in chunk:
            break
    return data

def parse_ascii_frame(frame):
    """Parse an ASCII LMDscandata telegram safely."""
    try:
        text = frame.decode("utf-8", errors="ignore")
    except Exception:
        return None

    if "LMDscandata" not in text:
        return None

    tokens = text.split()

    try:
        start_idx = tokens.index("LMDscandata")
        dist_idx = tokens.index("DIST1")
    except ValueError:
        print(" Frame missing expected keywords 'LMDscandata' or 'DIST1'.")
        return None

    # Extract start and step angles safely
    try:
        start_angle_raw = int(tokens[23], 16)
        step_angle_raw = int(tokens[24], 16)
    except (ValueError, IndexError):
        start_angle_raw = -1350000
        step_angle_raw = 3333  # Default to ~0.3333°

    start_angle = start_angle_raw / 10000.0
    step_angle = step_angle_raw / 10000.0

    # Get number of distance measurements
    try:
        num_points = int(tokens[dist_idx + 1], 16)
    except (ValueError, IndexError):
        print(" Could not parse point count, skipping frame.")
        return None

    # Prevent IndexError if telegram is truncated
    available_tokens = len(tokens) - (dist_idx + 2)
    safe_count = min(num_points, available_tokens)

    if safe_count < num_points:
        print(f" Short frame: expected {num_points} points, only {safe_count} tokens available.")
        num_points = safe_count

    distances = []
    for i in range(num_points):
        try:
            token = tokens[dist_idx + 2 + i]
            distances.append(int(token, 16))
        except (ValueError, IndexError):
            distances.append(0)

    return {
        "start_angle": start_angle,
        "step_angle": step_angle,
        "distances": distances
    }

def polar_to_cartesian(scan):
    """Convert polar (r, angle) points to Cartesian (x, y)."""
    x, y = [], []
    for i, r in enumerate(scan["distances"]):
        angle_deg = scan["start_angle"] + i * scan["step_angle"]
        angle_rad = math.radians(angle_deg)
        x.append(r * math.cos(angle_rad))
        y.append(r * math.sin(angle_rad))
    return x, y

# ----------------------------
# Live Visualization
# ----------------------------
def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((LIDAR_IP, LIDAR_PORT))
    print(f" Connected to LiDAR at {LIDAR_IP}:{LIDAR_PORT}")

    # Start continuous scan
    send_command(sock, "sEN LMDscandata 1")
    print("▶ LiDAR streaming started... (Ctrl+C to stop)")

    if SAVE_JSON:
        f = open(OUTPUT_FILE, "w")
        f.write("[\n")

    plt.ion()
    fig, ax = plt.subplots(figsize=(7,7))
    scat = ax.scatter([], [], s=2)
    ax.set_xlim(-5000, 5000)
    ax.set_ylim(-5000, 5000)
    ax.set_title("Live LiDAR Scan - Cartesian View")
    ax.set_xlabel("X (mm)")
    ax.set_ylabel("Y (mm)")
    ax.axis("equal")
    plt.show()

    try:
        frame_count = 0
        while True:
            frame = read_frame(sock)
            if not frame:
                continue

            scan = parse_ascii_frame(frame)
            if scan:
                x, y = polar_to_cartesian(scan)
                scat.set_offsets(list(zip(x, y)))
                fig.canvas.draw_idle()
                plt.pause(0.01)
                frame_count += 1

                if SAVE_JSON:
                    json_entry = {
                        "timestamp": datetime.now().isoformat(),
                        "points": [{"x": xi, "y": yi} for xi, yi in zip(x, y)]
                    }
                    f.write(json.dumps(json_entry) + ",\n")

                if frame_count % 20 == 0:
                    print(f" Frames processed: {frame_count}")

            else:
                print(" No valid scan data in this frame.")
                time.sleep(0.05)

    except KeyboardInterrupt:
        print("\n Stopping LiDAR stream...")
        send_command(sock, "sEN LMDscandata 0")
        if SAVE_JSON:
            f.write("{}]\n")
            f.close()
        sock.close()
        print(" Cleanly disconnected and stopped.")

if __name__ == "__main__":
    main()
