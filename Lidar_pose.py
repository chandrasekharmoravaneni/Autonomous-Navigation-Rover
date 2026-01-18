#!/usr/bin/env python3
import socket
import json
import math
import datetime
import time
import argparse
from typing import List, Tuple

import numpy as np

# ============================================================
# ----------------------------- TIM781 CONFIG ----------------
# ============================================================
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
    except Exception:
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
        except Exception:
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
            while vi + 1 < len(va) and va[vi + 1] < ang:
                vi += 1
            r = lerp(va[vi], vr[vi], va[vi + 1], vr[vi + 1], ang)

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
# RAW LIDAR COLLECTION
# -----------------------------------------------------------
def collect_lidar_frames():
    """
    Collects LiDAR frames from the TIM781 and saves them to OUTPUT_FILE.
    Returns the list of frames.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2.0)
    sock.connect((IP, PORT))

    print("Connected. Enabling scans...")
    send_command(sock, "sEN LMDscandata 1")

    frames = []
    buffer = ""

    print("Reading frames... (press Ctrl+C to stop)")

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
                packet = buffer[s + 1:e]
                buffer = buffer[e + 1:]

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

                print(f"Frame OK: {len(cart)} points (total frames: {len(frames)})")

                with open(OUTPUT_FILE, "w") as f:
                    json.dump(frames, f, indent=2)

            time.sleep(0.0005)

    except KeyboardInterrupt:
        print("\nStopping data collection...")
        with open(OUTPUT_FILE, "w") as f:
            json.dump(frames, f, indent=2)
        sock.close()
        print(f"Raw LiDAR data saved to: {OUTPUT_FILE}")

    return frames


# ============================================================
# ===================  ICP / Pose12 PART  ====================
# ============================================================

try:
    from scipy.spatial import cKDTree
    _HAS_SCIPY = True
except ImportError:
    _HAS_SCIPY = False


def load_tim781_scans(json_path: str) -> Tuple[List[str], List[np.ndarray]]:
    """
    Load scans from tim781_data.json-like file.

    Expected structure:
    [
      {
        "timestamp": "...",
        "points": [ {"x": ..., "y": ..., "angle": ...}, ... ]
      },
      ...
    ]

    Returns:
        timestamps: list of timestamps (as strings)
        scans: list of Nx2 numpy arrays (x,y) per scan
    """
    with open(json_path, "r") as f:
        data = json.load(f)

    timestamps: List[str] = []
    scans: List[np.ndarray] = []

    for entry in data:
        timestamps.append(entry["timestamp"])
        pts = entry["points"]
        xy = np.array([[p["x"], p["y"]] for p in pts], dtype=np.float64)
        scans.append(xy)

    return timestamps, scans


def nearest_neighbors(src: np.ndarray, dst: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """
    Find nearest neighbor in dst for each point in src.

    Args:
        src: Nx2 array
        dst: Mx2 array

    Returns:
        distances: N array of squared distances
        indices:   N array of indices in dst
    """
    if _HAS_SCIPY:
        tree = cKDTree(dst)
        dists, idx = tree.query(src)
        return dists ** 2, idx
    else:
        # Brute-force fallback: O(N*M). Fine for modest point counts.
        diff = src[:, None, :] - dst[None, :, :]  # N x M x 2
        dist2 = np.sum(diff ** 2, axis=2)         # N x M
        idx = np.argmin(dist2, axis=1)            # N
        dists = dist2[np.arange(src.shape[0]), idx]
        return dists, idx


def best_fit_transform(A: np.ndarray, B: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """
    Compute the best-fit 2D rigid transform (R,t) that maps A to B:

        B ≈ R @ A + t
    """
    assert A.shape == B.shape

    centroid_A = np.mean(A, axis=0)
    centroid_B = np.mean(B, axis=0)

    AA = A - centroid_A
    BB = B - centroid_B

    H = AA.T @ BB  # 2x2

    U, S, Vt = np.linalg.svd(H)
    R = Vt.T @ U.T

    if np.linalg.det(R) < 0:
        Vt[1, :] *= -1
        R = Vt.T @ U.T

    t = centroid_B - R @ centroid_A

    return R, t


def icp_2d(
    src: np.ndarray,
    dst: np.ndarray,
    max_iterations: int = 50,
    tolerance: float = 1e-5,
    reject_outlier_quantile: float = 0.95,
) -> Tuple[np.ndarray, float, int]:
    """
    Perform 2D ICP to align src onto dst.

    We solve for T such that:

        dst ≈ T @ src

    where T is a 3x3 homogeneous transform.
    """
    T = np.eye(3)
    src_h = np.hstack([src, np.ones((src.shape[0], 1))])  # Nx3
    src_transformed = src.copy()

    prev_error = float("inf")

    for i in range(max_iterations):
        distances, indices = nearest_neighbors(src_transformed, dst)
        matched_dst = dst[indices]

        # Optional outlier rejection
        if 0 < reject_outlier_quantile < 1.0:
            thresh = np.quantile(distances, reject_outlier_quantile)
            mask = distances <= thresh
            if np.sum(mask) >= 3:
                matched_src = src_transformed[mask]
                matched_dst = matched_dst[mask]
                distances = distances[mask]
            else:
                matched_src = src_transformed
        else:
            matched_src = src_transformed

        R, t = best_fit_transform(matched_src, matched_dst)

        R_h = np.eye(3)
        R_h[:2, :2] = R
        R_h[:2, 2] = t

        T = R_h @ T

        src_transformed = (R_h @ src_h.T).T[:, :2]

        mse = float(np.mean(distances))
        if abs(prev_error - mse) < tolerance:
            return T, mse, i + 1
        prev_error = mse

    return T, prev_error, max_iterations


def transform_to_xyyaw(T: np.ndarray) -> Tuple[float, float, float]:
    """
    Extract (x, y, yaw) from a 3x3 SE(2) transform matrix.
    """
    x = T[0, 2]
    y = T[1, 2]
    yaw = math.atan2(T[1, 0], T[0, 0])
    return x, y, yaw


def compute_poses_from_scans(
    scans: List[np.ndarray],
    max_iterations: int = 50,
    tolerance: float = 1e-5,
    downsample_step: int = 2,
) -> List[np.ndarray]:
    """
    Compute global poses for a sequence of 2D LiDAR scans using ICP between
    consecutive scans.
    """
    poses: List[np.ndarray] = [np.eye(3)]

    for k in range(1, len(scans)):
        prev_pts = scans[k - 1]
        curr_pts = scans[k]

        if downsample_step > 1:
            prev_pts = prev_pts[::downsample_step]
            curr_pts = curr_pts[::downsample_step]

        T_rel, mse, iters = icp_2d(
            src=prev_pts,
            dst=curr_pts,
            max_iterations=max_iterations,
            tolerance=tolerance,
        )

        T_world_prev = poses[-1]
        T_world_curr = T_world_prev @ T_rel
        poses.append(T_world_curr)

        print(
            f"ICP scan {k-1} -> {k}: mse={mse:.6f}, iters={iters}, "
            f"pose=(x={T_world_curr[0,2]:.3f}, y={T_world_curr[1,2]:.3f}, "
            f"yaw={math.degrees(math.atan2(T_world_curr[1,0], T_world_curr[0,0])):.2f} deg)"
        )

    return poses


def save_poses_csv(out_path: str, timestamps: List[str], poses: List[np.ndarray]) -> None:
    """
    Save poses as CSV: timestamp,x,y,yaw_rad,yaw_deg
    """
    import csv

    with open(out_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "x", "y", "yaw_rad", "yaw_deg"])
        for ts, T in zip(timestamps, poses):
            x, y, yaw = transform_to_xyyaw(T)
            writer.writerow(
                [ts, f"{x:.6f}", f"{y:.6f}", f"{yaw:.9f}", f"{math.degrees(yaw):.6f}"]
            )


def save_poses_json(out_path: str, timestamps: List[str], poses: List[np.ndarray]) -> None:
    """
    Save poses as JSON:
    [
      { "timestamp": "...", "x": ..., "y": ..., "yaw_rad": ..., "yaw_deg": ... },
      ...
    ]
    """
    entries = []
    for ts, T in zip(timestamps, poses):
        x, y, yaw = transform_to_xyyaw(T)
        entries.append(
            {
                "timestamp": ts,
                "x": x,
                "y": y,
                "yaw_rad": yaw,
                "yaw_deg": math.degrees(yaw),
            }
        )

    with open(out_path, "w") as f:
        json.dump(entries, f, indent=2)


def run_icp_on_file(json_path: str,
                    max_iters: int = 50,
                    tol: float = 1e-5,
                    downsample_step: int = 2,
                    out_csv: str = "poses_icp.csv",
                    out_json: str = "poses_icp.json") -> None:
    """
    Convenience wrapper: load scans from json_path, run ICP, save CSV + JSON.
    """
    timestamps, scans = load_tim781_scans(json_path)
    print(f"\nLoaded {len(scans)} scans from {json_path}")

    poses = compute_poses_from_scans(
        scans,
        max_iterations=max_iters,
        tolerance=tol,
        downsample_step=downsample_step,
    )

    save_poses_csv(out_csv, timestamps, poses)
    save_poses_json(out_json, timestamps, poses)

    print(f"Pose CSV  saved to: {out_csv}")
    print(f"Pose JSON saved to: {out_json}")


# ============================================================
# =======================   MAIN   ===========================
# ============================================================
def main():
    # 1) Collect raw LiDAR data from the sensor
    frames = collect_lidar_frames()
    if not frames:
        print("No frames collected, skipping ICP.")
        return

    # 2) Run ICP on the saved JSON file and output pose CSV + JSON
    run_icp_on_file(OUTPUT_FILE)


if __name__ == "__main__":
    main()
