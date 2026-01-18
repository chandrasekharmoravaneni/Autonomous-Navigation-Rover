#!/usr/bin/env python3

import socket
import math
import json
from datetime import datetime

# =========================================================
# CONFIG
# =========================================================
LIDAR_IP = "192.168.0.1"
LIDAR_PORT = 2111
SAVE_JSON = True
OUTPUT_FILE = "lidar_tim781_811points3.json"
UNIT = "mm"    # or "m"

STX = b'\x02'
ETX = b'\x03'

# FIXED TIM781 SCAN GEOMETRY
START_ANGLE = -45.0
STEP_ANGLE = 0.3333
MIN_DIST = 50
MAX_DIST = 25000


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
# PARSER FOR TIM781
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

    offset = idx + 4  # skip meta count etc.

    distances = []
    for tok in tokens[offset:]:
        try:
            distances.append(int(tok, 16))
        except:
            break

    if len(distances) < 700:  # must be full scan (typically 811)
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
    factor = 0.001 if UNIT == "m" else 1.0

    for i, r in enumerate(scan["distances"]):

        if r < MIN_DIST or r > MAX_DIST:
            r = 0

        angle_deg = scan["start_angle"] + i * scan["step_angle"]
        angle_rad = math.radians(angle_deg)

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

    send_command(sock, "sWN SetToAscii 1")
    send_command(sock, "sEN LMDscandata 1")
    print("Streaming... Press Ctrl+C to stop.")

    if SAVE_JSON:
        f = open(OUTPUT_FILE, "w")
        f.write("{\n")

    frame_id = 0
    first = True

    try:
        while True:

            raw = read_frame(sock)
            scan = parse_ascii_frame(raw)
            if not scan:
                continue

            distances = scan["distances"]
            num_points = len(distances)

            # === THIS IS YOUR 811 POINTS OUTPUT ===
            print(f"Frame → {num_points} points")

            # Convert to XY
            xs, ys, angs = polar_to_cartesian(scan)

            frame_id += 1
            ts = datetime.now().isoformat()

            points = [
                [float(f"{x:.3f}"), float(f"{y:.3f}"), float(f"{a:.3f}")]
                for x, y, a in zip(xs, ys, angs)
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

    except KeyboardInterrupt:
        print("\nStopping...")

        send_command(sock, "sEN LMDscandata 0")

        if SAVE_JSON:
            f.write("\n}\n")
            f.close()
            print(f"JSON saved → {OUTPUT_FILE}")

        sock.close()
        print(f"Total frames saved: {frame_id}")


if __name__ == "__main__":
    main()
