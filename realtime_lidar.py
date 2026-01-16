#!/usr/bin/env python3
"""
TIM781 safe writer — timestamped file only (no 'latest' file).
- Ensures exactly NUM_POINTS (811) per frame, angles -45..225 inclusive.
- Writes timestamped file atomically so on-disk JSON is always valid.
- Optional NDJSON mode for memory-friendly streaming.
"""

import socket
import math
import json
from datetime import datetime
import time
import os
import tempfile
import sys

# ============= CONFIG =============
LIDAR_IP = "192.168.0.1"
LIDAR_PORT = 2111

UNIT = "mm"           # "mm" or "m"
SAVE_JSON = True

# If True, use NDJSON for timestamped file (memory-friendly).
# If False, keep full JSON object and perform atomic replace each frame.
USE_NDJSON = False

STX = b'\x02'
ETX = b'\x03'

# Geometry (fixed)
START_ANGLE = -45.0
END_ANGLE = 225.0
NUM_POINTS = 811
STEP_ANGLE = (END_ANGLE - START_ANGLE) / (NUM_POINTS - 1)

MIN_DIST = 50
MAX_DIST = 25000

# Socket read timeout
READ_TIMEOUT = 2.0

# ============= Helpers =============
def send_command(sock, cmd):
    sock.sendall(STX + cmd.encode() + ETX)

def read_frame(sock, timeout_seconds=READ_TIMEOUT):
    sock.settimeout(timeout_seconds)
    data = b""
    try:
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            data += chunk
            if ETX in chunk:
                break
    except socket.timeout:
        pass
    except Exception:
        pass
    return data

def safe_atomic_write_json(path, obj):
    """
    Write obj (python-serializable) to path atomically:
    1) write to a temp file in same directory
    2) flush + fsync
    3) os.replace(temp, path)
    Ensures `path` is always valid JSON (old or new).
    """
    dirn = os.path.dirname(path) or "."
    fd, tmp_path = tempfile.mkstemp(prefix=".tmp_", dir=dirn, text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=2)
            f.write("\n")
            f.flush()
            try:
                os.fsync(f.fileno())
            except Exception:
                pass
        os.replace(tmp_path, path)
    except Exception:
        try:
            os.remove(tmp_path)
        except Exception:
            pass
        raise

# ============= Parser =============
def parse_ascii_frame(frame_bytes):
    if not frame_bytes:
        return None
    try:
        text = frame_bytes.decode("utf-8", errors="ignore")
    except Exception:
        return None
    if "LMDscandata" not in text:
        return None
    tokens = text.replace("\r", " ").replace("\n", " ").split()
    try:
        idx = tokens.index("DIST1")
    except ValueError:
        return None
    distances = []
    # collect up to NUM_POINTS hex tokens only
    for tok in tokens[idx+1:]:
        if len(distances) >= NUM_POINTS:
            break
        try:
            val = int(tok, 16)
            distances.append(val)
        except Exception:
            continue
    # pad or trim to exactly NUM_POINTS
    if len(distances) < NUM_POINTS:
        distances += [0] * (NUM_POINTS - len(distances))
    elif len(distances) > NUM_POINTS:
        distances = distances[:NUM_POINTS]
    return {"distances": distances}

# ============= Conversion =============
def polar_to_point_objects(distances):
    points = []
    factor = 0.001 if UNIT == "m" else 1.0
    ts = datetime.now().isoformat()
    for i, r in enumerate(distances):
        angle_deg = START_ANGLE + i * STEP_ANGLE
        if r < MIN_DIST or r > MAX_DIST:
            xr, yr = 0.0, 0.0
        else:
            rad = math.radians(angle_deg)
            xr = r * math.cos(rad) * factor
            yr = r * math.sin(rad) * factor
        points.append({
            "timestamp": ts,
            "x": float(f"{xr:.3f}"),
            "y": float(f"{yr:.3f}"),
            "angle": float(f"{angle_deg:.3f}")
        })
    # defensive pad/trim
    if len(points) < NUM_POINTS:
        for i in range(len(points), NUM_POINTS):
            angle_deg = START_ANGLE + i * STEP_ANGLE
            points.append({"timestamp": ts, "x": 0.0, "y": 0.0, "angle": float(f"{angle_deg:.3f}")})
    elif len(points) > NUM_POINTS:
        points = points[:NUM_POINTS]
    return points

# ============= Main =============
def main():
    now = datetime.now()
    ts_for_name = now.strftime("%Y%m%d_%H%M%S")
    timestamped_filename = f"lidar_{ts_for_name}.json"

    frames = {}  # keeps all frames for current run if not NDJSON
    frame_id = 0

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect((LIDAR_IP, LIDAR_PORT))
    except Exception as e:
        print(f"Failed to connect to {LIDAR_IP}:{LIDAR_PORT} -> {e}")
        return

    print(f"Connected → {LIDAR_IP}:{LIDAR_PORT}")
    try:
        send_command(sock, "sWN SetToAscii 1")
        send_command(sock, "sEN LMDscandata 1")
    except Exception as e:
        print("Failed to send start commands:", e)
        sock.close()
        return

    print("Streaming... Press Ctrl+C to stop.")
    if USE_NDJSON:
        open(timestamped_filename, "w").close()
        print("Using NDJSON for timestamped file:", timestamped_filename)
    else:
        print("Using atomic full-JSON for timestamped file:", timestamped_filename)

    try:
        while True:
            raw = read_frame(sock)
            if not raw:
                time.sleep(0.005)
                continue
            parsed = parse_ascii_frame(raw)
            if not parsed:
                continue
            distances = parsed["distances"]
            points = polar_to_point_objects(distances)
            frame_id += 1
            key = f"frame_{frame_id}"

            if SAVE_JSON:
                if USE_NDJSON:
                    # append per-line JSON object (memory-friendly)
                    line_obj = { key: points }
                    with open(timestamped_filename, "a", encoding="utf-8") as f:
                        f.write(json.dumps(line_obj, ensure_ascii=False) + "\n")
                        f.flush()
                        try:
                            os.fsync(f.fileno())
                        except Exception:
                            pass
                else:
                    frames[key] = points
                    # write entire frames dict atomically
                    safe_atomic_write_json(timestamped_filename, frames)

            print(f"Frame {frame_id} written → {NUM_POINTS} points (angles {START_ANGLE:.3f} .. {END_ANGLE:.3f})")

    except KeyboardInterrupt:
        print("\nStopping (KeyboardInterrupt)...")
    except Exception as e:
        print("Exception:", e)
    finally:
        try:
            send_command(sock, "sEN LMDscandata 0")
        except Exception:
            pass
        sock.close()
        print(f"Total frames captured: {frame_id}")
        # final write / ensure file is up-to-date
        if SAVE_JSON and not USE_NDJSON:
            try:
                safe_atomic_write_json(timestamped_filename, frames)
                print("Final timestamped JSON written atomically:", timestamped_filename)
            except Exception as e:
                print("Error writing final file:", e)
        elif SAVE_JSON and USE_NDJSON:
            print("NDJSON timestamped file available:", timestamped_filename)

if __name__ == "__main__":
    main()