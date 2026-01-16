import socket
import json
import math
import datetime
import time

# -----------------------------
# TIM781 CONFIG
# -----------------------------
IP = "192.168.0.1"
PORT = 2111
OUTPUT_FILE = "tim781_data_811.json"

START_ANGLE = -45.0
POINT_COUNT = 811
SPAN_DEG = 270.0
CANON_RES = SPAN_DEG / (POINT_COUNT - 1)   # correct: 270/(811-1)

STX = "\x02"
ETX = "\x03"

def send_command(sock, cmd):
    msg = f"{STX}{cmd}{ETX}"
    sock.sendall(msg.encode())

def lerp(x0, y0, x1, y1, x):
    if x1 == x0:
        return y0
    return y0 + (y1 - y0) * (x - x0) / (x1 - x0)

# -----------------------------------------------------------
# PARSE + RESAMPLE to 811 points
# -----------------------------------------------------------
def parse_and_resample(block):
    parts = block.split()
    if "DIST1" not in parts:
        return None

    idx = parts.index("DIST1")

    try:
        count_hex = parts[idx + 4]
        count = int(count_hex, 16)
    except:
        return None

    start = idx + 5
    end = start + count
    if "RSSI1" in parts[start:]:
        end = parts.index("RSSI1")
    end = min(end, len(parts))

    raw_hex = parts[start:end]

    # Convert hex → meters (invalid → None)
    values = []
    for h in raw_hex:
        try:
            values.append(int(h, 16) / 1000.0)
        except:
            values.append(None)

    if len(values) == 0:
        values = [None] * POINT_COUNT

    # Build measured angle list
    if len(values) == 1:
        measured_angles = [START_ANGLE]
    else:
        step = SPAN_DEG / (len(values) - 1)
        measured_angles = [START_ANGLE + i * step for i in range(len(values))]

    canonical_angles = [START_ANGLE + i * CANON_RES for i in range(POINT_COUNT)]

    # Extract only valid points for interpolation
    valid = [(a, r) for a, r in zip(measured_angles, values) if r is not None]

    if len(valid) == 0:
        # No real data – return None for all
        return [{"angle": ang, "range": None} for ang in canonical_angles]

    if len(valid) == 1:
        only_r = valid[0][1]
        return [{"angle": ang, "range": only_r} for ang in canonical_angles]

    # Interpolation
    resampled = []
    va = [p[0] for p in valid]
    vr = [p[1] for p in valid]
    vi = 0

    for ang in canonical_angles:
        if ang <= va[0]:
            r = vr[0]
        elif ang >= va[-1]:
            r = vr[-1]
        else:
            while vi + 1 < len(va) and va[vi+1] < ang:
                vi += 1
            r = lerp(va[vi], vr[vi], va[vi+1], vr[vi+1], ang)

        resampled.append({"angle": ang, "range": r})

    return resampled

# -----------------------------------------------------------
# POLAR → CARTESIAN (NO range field in output)
# -----------------------------------------------------------
def polar_to_cartesian(points):
    cart = []
    for p in points:
        a = math.radians(p["angle"])
        r = p["range"]
        if r is None:
            x = None
            y = None
        else:
            x = r * math.cos(a)
            y = r * math.sin(a)

        cart.append({
            "x": x,
            "y": y,
            "angle": p["angle"]
        })
    return cart

# -----------------------------------------------------------
# MAIN LOOP
# -----------------------------------------------------------
def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2.0)
    sock.connect((IP, PORT))

    print("Connected. Enabling scans...")
    send_command(sock, "sEN LMDscandata 1")

    frames = []
    buffer = ""

    print("Reading frames...")

    try:
        while True:
            try:
                data = sock.recv(65535).decode(errors="ignore")
                buffer += data
            except socket.timeout:
                pass

            # Extract full packets
            while STX in buffer and ETX in buffer:
                s = buffer.index(STX)
                e = buffer.index(ETX, s + 1)
                packet = buffer[s+1:e]
                buffer = buffer[e+1:]

                if "LMDscandata" not in packet:
                    continue

                polar = parse_and_resample(packet)
                if polar is None:
                    continue

                cart = polar_to_cartesian(polar)

                frame = {
                    "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
                    "points": cart
                }
                frames.append(frame)

                print(f"Frame OK: {len(cart)} points")

                with open(OUTPUT_FILE, "w") as f:
                    json.dump(frames, f, indent=2)

            time.sleep(0.0005)

    except KeyboardInterrupt:
        print("Stopping...")
        with open(OUTPUT_FILE, "w") as f:
            json.dump(frames, f, indent=2)
        sock.close()

if __name__ == "__main__":
    main()
