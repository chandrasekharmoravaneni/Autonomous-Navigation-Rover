#!/usr/bin/env python3
"""
TIM781 – FULL FIXED VERSION
Includes:
✔ AccessMode unlock
✔ Scan config read
✔ Attempt to set full 270° (811 points)
✔ Live polar plot (working)
✔ JSON frame capture
"""

import socket
import math
import json
import matplotlib.pyplot as plt
import time
from datetime import datetime


# =========================================================
# CONFIG
# =========================================================
LIDAR_IP = "192.168.0.1"
LIDAR_PORT = 2111
SAVE_JSON = True
OUTPUT_FILE = "lidar_live_full_fix.json"
UNIT = "mm"

STX = b'\x02'
ETX = b'\x03'

MIN_DIST = 50
MAX_DIST = 25000


# =========================================================
# SOPAS HELPERS
# =========================================================
def send_command(sock, cmd):
    sock.sendall(STX + cmd.encode() + ETX)


def read_frame(sock, timeout=2.0):
    sock.settimeout(timeout)
    data = b""
    start = time.time()
    try:
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            data += chunk
            if ETX in chunk:
                break
            if time.time() - start > timeout:
                break
    except:
        pass
    return data


# =========================================================
# READ SCAN CONFIG (IMPORTANT)
# =========================================================
def read_scan_cfg(sock):
    send_command(sock, "sRN LMPscancfg")
    time.sleep(0.05)
    resp = read_frame(sock)
    try:
        return resp.decode("utf-8", errors="ignore")
    except:
        return str(resp)


# =========================================================
# TRY SET FULL 270° MODE
# =========================================================
def try_set_full_scan(sock):
    send_command(sock, "sMN mLMPsetscancfg -4500 22500 3333 0 0")
    time.sleep(0.1)
    send_command(sock, "sMN mEEwriteall")
    time.sleep(0.1)
    return read_scan_cfg(sock)


# =========================================================
# PARSE LMDscandata ASCII
# =========================================================
def parse_ascii_frame(frame):
    if not frame:
        return None

    text = frame.decode("utf-8", errors="ignore")

    if "LMDscandata" not in text:
        return None

    tokens = text.split()

    try:
        dist_idx = tokens.index("DIST1")
    except:
        return None

    try:
        num_points = int(tokens[dist_idx + 1], 16)
    except:
        return None

    # ---- Parse distances ----
    distances = []
    for i in range(num_points):
        try:
            distances.append(int(tokens[dist_idx + 2 + i], 16))
        except:
            distances.append(0)

    # ---- Parse start angle and step angle ----
    start_angle = -45.0
    step_angle = 0.3333

    for tok in tokens:
        try:
            val = int(tok, 16)
        except:
            continue

        # Start angle encoded as signed int *10000
        if abs(val) > 100000 and abs(val) < 4000000:
            if val & (1 << 31):
                val -= (1 << 32)
            start_angle = val / 10000.0

        # step angle 3333 → 0.3333
        if 1 < val < 20000:
            step_angle = val / 10000.0

    return {
        "start_angle": start_angle,
        "step_angle": step_angle,
        "distances": distances
    }


# =========================================================
# CARTESIAN + ANGLES
# =========================================================
def polar_to_cartesian(scan):
    xs, ys, angs = [], [], []

    for i, r in enumerate(scan["distances"]):
        if r < MIN_DIST or r > MAX_DIST:
            continue

        angle_deg = scan["start_angle"] + i * scan["step_angle"]
        angle_rad = math.radians(angle_deg)

        factor = 0.001 if UNIT == "m" else 1.0

        xs.append(r * math.cos(angle_rad) * factor)
        ys.append(r * math.sin(angle_rad) * factor)
        angs.append(angle_deg)

    return xs, ys, angs


# =========================================================
# MAIN
# =========================================================
def main():
    # ---- CONNECT ----
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((LIDAR_IP, LIDAR_PORT))
    print("Connected.")

    # ---- UNLOCK ACCESS MODE 3 ----
    print("Unlocking scanner (Access Mode 3)...")
    send_command(sock, "sMN SetAccessMode 03 F4724744")
    time.sleep(0.1)
    unlock_resp = read_frame(sock).decode("utf-8", errors="ignore")
    print("UNLOCK RESPONSE:", unlock_resp)

    # ---- READ CONFIG (BEFORE) ----
    print("\nReading current scan configuration...")
    cfg_before = read_scan_cfg(sock)
    print("RAW SCAN CFG BEFORE:", cfg_before.strip())

    # ---- TRY ENABLE FULL 270° ----
    print("\nTrying to enable full 270° scan (811 points)...")
    cfg_after = try_set_full_scan(sock)
    print("RAW SCAN CFG AFTER:", cfg_after.strip())

    # ---- ENABLE ASCII + DATA ----
    send_command(sock, "sWN SetToAscii 1")
    time.sleep(0.05)
    send_command(sock, "sEN LMDscandata 1")
    print("\nLMDscandata streaming enabled.\n")

    # ---- JSON ----
    if SAVE_JSON:
        f = open(OUTPUT_FILE, "w")
        f.write("{\n")

    # ---- PLOT ----
    plt.ion()
    fig = plt.figure(figsize=(8, 8))
    ax = fig.add_subplot(111, projection='polar')

    ax.set_theta_zero_location("E")
    ax.set_theta_direction(-1)
    ax.set_rmax(6000)
    plt.show()

    frame_id = 0
    first = True

    try:
        while True:
            raw = read_frame(sock)
            scan = parse_ascii_frame(raw)
            if not scan:
                continue

            xs, ys, angs = polar_to_cartesian(scan)
            if not xs:
                continue

            # ---- Polar update ----
            ax.clear()
            ax.set_theta_zero_location("E")
            ax.set_theta_direction(-1)
            ax.set_rmax(6000)

            thetas = [math.atan2(y, x) for x, y in zip(xs, ys)]
            rvals = [math.hypot(x, y) for x, y in zip(xs, ys)]

            ax.scatter(thetas, rvals, s=4)

            fig.canvas.draw()
            fig.canvas.flush_events()
            plt.pause(0.001)

            # ---- JSON Save ----
            frame_id += 1
            data_points = [
                {"x": round(x, 3), "y": round(y, 3), "ang": round(a, 3)}
                for x, y, a in zip(xs, ys, angs)
            ]

            if SAVE_JSON:
                if not first:
                    f.write(",\n")
                first = False
                f.write(f'  "frame_{frame_id}": ')
                f.write(json.dumps(data_points))

            print(f"Frame {frame_id} → {len(xs)} points")

    except KeyboardInterrupt:
        print("\nStopping...")
        send_command(sock, "sEN LMDscandata 0")
        sock.close()
        if SAVE_JSON:
            f.write("\n}\n")
            f.close()
        print("Saved JSON:", OUTPUT_FILE)


if __name__ == "__main__":
    main()
