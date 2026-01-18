#!/usr/bin/env python3

import socket
import math
import json
import matplotlib.pyplot as plt
from datetime import datetime


# =========================================================
# CONFIG
# =========================================================
LIDAR_IP = "192.168.0.1"
LIDAR_PORT = 2111
SAVE_JSON = True
OUTPUT_FILE = "lidar_tim781_frame_test7.json"
UNIT = "mm"    # or "m"

STX = b'\x02'
ETX = b'\x03'

# FIXED TIM781 SCAN GEOMETRY
START_ANGLE = -45.0      # degrees (native)
STEP_ANGLE = 0.3333      # degrees
MIN_DIST = 50            # mm
MAX_DIST = 25000         # mm


# =========================================================
# SEND COMMAND
# =========================================================
def send_command(sock, cmd):
    sock.sendall(STX + cmd.encode() + ETX)


def read_frame(sock):
    data = b""
    while True:
        chunk = sock.recv(4096)
        if not chunk:
            break
        data += chunk
        if ETX in chunk:
            break
    return data


# =========================================================
# PARSER FOR TIM781 (ASCII LMDscandata)
# =========================================================
def parse_ascii_frame(frame):
    try:
        text = frame.decode("utf-8", errors="ignore")
    except:
        return None

    if "LMDscandata" not in text:
        return None

    tokens = text.split()

    # DIST1 block
    try:
        idx = tokens.index("DIST1")
    except:
        return None

    # skip metadata (3 tokens)
    offset = idx + 4

    distances = []
    for tok in tokens[offset:]:
        try:
            distances.append(int(tok, 16))
        except:
            break

    if len(distances) < 100:
        return None

    return {
        "start_angle": START_ANGLE,
        "step_angle": STEP_ANGLE,
        "distances": distances
    }


# =========================================================
# POLAR → CARTESIAN
# =========================================================
def polar_to_cartesian(scan):
    xs, ys, angs = [], [], []

    for i, r in enumerate(scan["distances"]):

        if r < MIN_DIST or r > MAX_DIST:
            r = 0

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
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((LIDAR_IP, LIDAR_PORT))
    print(f"Connected → {LIDAR_IP}:{LIDAR_PORT}")

    # ------------------------------------------------------
    # FORCE FULL 270° SCAN MODE (FIX FOR 811 POINTS)
    # ------------------------------------------------------
    print("Configuring full 270° scan output...")
    send_command(sock, "sMN mLMPsetscancfg -4500 22500 3333 0 0")  # <--- FIX
    send_command(sock, "sMN mEEwriteall")                          # <--- SAVE CONFIG
    print("Configuration applied. (Reboot may be required the first time)")

    # Enable ASCII + scanning
    send_command(sock, "sWN SetToAscii 1")
    send_command(sock, "sEN LMDscandata 1")
    print("TIM781 Streaming... (Ctrl+C to stop)")

    # Open JSON file
    if SAVE_JSON:
        f = open(OUTPUT_FILE, "w")
        f.write("{\n")

    # ======================================================
    # SOPAS FULL-CIRCLE POLAR VIEW
    # ======================================================
    plt.ion()
    fig = plt.figure(figsize=(9, 9))
    ax = fig.add_subplot(111, projection='polar')

    scat = ax.scatter([], [], s=4)

    ax.set_theta_zero_location("E")
    ax.set_theta_direction(1)
    ax.set_thetamin(0)
    ax.set_thetamax(360)
    ax.set_rmax(25000 if UNIT == "mm" else 25)

    sopas_ticks = [0, 45, 90, 135, 180, 225, 270, 315]
    ax.set_xticks([math.radians(d) for d in sopas_ticks])
    ax.set_xticklabels([f"{d}°" for d in sopas_ticks])

    ax.set_title("TIM781 Scan — SOPAS Full View", pad=20)
    plt.show()

    # ======================================================
    # LOOP
    # ======================================================
    frame_id = 0
    first = True

    try:
        while True:

            raw = read_frame(sock)
            if not raw:
                continue

            scan = parse_ascii_frame(raw)
            if not scan:
                continue

            distances = scan["distances"]
            num_points = len(distances)

            # Print number of points (720, 801, 812, etc.)
            print(f"Frame detected → {num_points} points")

            # Convert to Cartesian
            xs, ys, angs = polar_to_cartesian(scan)

            # Live polar plot
            thetas = [math.radians(a) for a in angs]
            rvals = [math.hypot(xi, yi) for xi, yi in zip(xs, ys)]

            try:
                scat.remove()
            except:
                pass

            scat = ax.scatter(thetas, rvals, s=4)
            fig.canvas.draw_idle()
            plt.pause(0.001)

            # Save JSON
            frame_id += 1
            ts = datetime.now().isoformat()

            points = [
                [float(f"{xi:.3f}"), float(f"{yi:.3f}"), float(f"{ai:.3f}")]
                for xi, yi, ai in zip(xs, ys, angs)
            ]

            frame_obj = {
                "ts": ts,
                "start_angle": START_ANGLE,
                "step_angle": STEP_ANGLE,
                "points": points
            }

            if SAVE_JSON:
                if not first:
                    f.write(",\n")
                first = False

                f.write(f'  "frame_{frame_id}": ')
                f.write(json.dumps(frame_obj))

            print(f"Frame saved: {frame_id}")

    except KeyboardInterrupt:
        print("\nStopping TIM781...")
        send_command(sock, "sEN LMDscandata 0")

        if SAVE_JSON:
            f.write("\n}\n")
            f.close()

        sock.close()
        print("Disconnected.")
        print(f"Total frames saved → {frame_id}")
        print(f"Saved JSON → {OUTPUT_FILE}")


if __name__ == "__main__":
    main()

