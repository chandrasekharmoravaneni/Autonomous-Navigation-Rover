#!/usr/bin/env python3
"""
build_slam_map.py

- Read ALL frames from lidar file (full JSON or NDJSON)
- For each consecutive frame compute 2D rigid transform using ICP (point-to-point)
- Chain transforms to estimate trajectory
- Accumulate transformed points into occupancy grid and plot map + trajectory

Usage:
  - Edit JSON_FILE to point to your timestamped lidar file (or NDJSON).
  - Run: python3 build_slam_map.py
"""

import json
import os
import math
import numpy as np
from scipy.spatial import cKDTree
import matplotlib.pyplot as plt
from datetime import datetime

# -------------------------
# Config - edit as needed
# -------------------------
JSON_FILE = "lidar_20250826_192038.json"   # <<-- set your filename
FRAME_SUBSAMPLE = 1      # use every Nth frame (speed vs accuracy)
POINT_SUBSAMPLE = 4      # keep 1 in K points from each scan (speed)
MAX_ICP_ITERS = 40
ICP_TOL = 1e-4           # convergence tol on mean error change
MAX_MATCH_DIST = 1000.0  # max correspondence distance (in same units as x/y)
MAP_RESOLUTION = 50.0    # grid cell size in units (e.g., mm) -> lower => higher res
MAP_PADDING = 20000      # mm padding around point cloud bounding box
MIN_POINTS_PER_SCAN = 50
# -------------------------

def read_all_frames(path):
    """Read all frames. Supports full JSON {frame_1: [...]} or NDJSON (one JSON obj per line)."""
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    frames = {}
    # first try full JSON
    try:
        with open(path, "r", encoding="utf-8") as f:
            obj = json.load(f)
        if isinstance(obj, dict) and any(k.startswith("frame_") for k in obj.keys()):
            frames = dict(sorted(obj.items(), key=lambda kv: int(kv[0].split("_")[1])))
            return frames
    except Exception:
        pass

    # fallback NDJSON
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                for k, v in obj.items():
                    frames[k] = v
            except Exception:
                continue
    frames = dict(sorted(frames.items(), key=lambda kv: int(kv[0].split("_")[1])))
    return frames

def scan_to_xy(points_list):
    """Given a list of point dicts return Nx2 numpy array of (x,y)."""
    xs = []
    ys = []
    for p in points_list:
        # p expected to have 'x' and 'y' floats
        try:
            xs.append(float(p.get("x", 0.0)))
            ys.append(float(p.get("y", 0.0)))
        except:
            xs.append(0.0); ys.append(0.0)
    return np.vstack((np.array(xs), np.array(ys))).T  # shape (N,2)

def downsample_points(pts, k):
    """Return every k-th point (fast simple downsample)."""
    if k <= 1:
        return pts
    return pts[::k]

# -------------------------
# 2D Point-to-Point ICP
# -------------------------
def icp_point_to_point(src_pts, dst_pts, max_iters=30, tol=1e-4, max_correspondence_dist=1e9):
    """
    Simple 2D point-to-point ICP.
    Input: src_pts (N,2) - points to transform to align with dst_pts
           dst_pts (M,2)
    Returns: cumulative transform (R, t) where R is 2x2, t is 2-vector
             and final mean error
    """
    src = src_pts.copy()
    dst_tree = cKDTree(dst_pts)
    T_R = np.eye(2)
    T_t = np.zeros(2)
    prev_error = None

    for it in range(max_iters):
        # find nearest neighbors (compatibly call query without n_jobs)
        dists, inds = dst_tree.query(src, k=1)
        # ensure shapes are (N,)
        dists = np.asarray(dists).reshape(-1)
        inds = np.asarray(inds).reshape(-1)

        mask = dists < max_correspondence_dist
        if mask.sum() < 6:
            # not enough correspondences to compute a reliable transform
            # return identity (no motion) and a large error
            return np.eye(2), np.zeros(2), np.inf

        src_matched = src[mask]
        dst_matched = dst_pts[inds[mask]]

        # compute centroids
        mu_s = src_matched.mean(axis=0)
        mu_d = dst_matched.mean(axis=0)
        # demean and compute cross-covariance
        S = (src_matched - mu_s).T @ (dst_matched - mu_d)
        # SVD
        U, _, Vt = np.linalg.svd(S)
        R = Vt.T @ U.T
        # ensure rotation (determinant +1)
        if np.linalg.det(R) < 0:
            Vt[1, :] *= -1
            R = Vt.T @ U.T
        t = mu_d - R @ mu_s

        # apply to source
        src = (R @ src.T).T + t

        # accumulate transform: new T = [R, t] * previous
        T_R = R @ T_R
        T_t = R @ T_t + t

        mean_error = np.mean(dists[mask])
        if prev_error is not None and abs(prev_error - mean_error) < tol:
            break
        prev_error = mean_error

    return T_R, T_t, prev_error if prev_error is not None else np.inf


# -------------------------
# Utility transforms
# -------------------------
def transform_points(pts, R, t):
    """Apply 2x2 R and 2-vector t to pts Nx2."""
    return (R @ pts.T).T + t

def compose_transform(R2, t2, R1, t1):
    """Return composed transform (R2,t2) o (R1,t1)."""
    R = R2 @ R1
    t = R2 @ t1 + t2
    return R, t

def rotmat_from_angle(theta):
    c = math.cos(theta); s = math.sin(theta)
    return np.array([[c, -s],[s, c]])

def angle_from_rotmat(R):
    return math.atan2(R[1,0], R[0,0])

# -------------------------
# Build map
# -------------------------
def build_map(all_points_world, resolution=50.0, padding=20000.0):
    """
    all_points_world: (K,2) numpy array in same units as lidar (likely mm)
    resolution: cell size in same unit (e.g., 50 mm ~ 5cm cells)
    """
    xs = all_points_world[:,0]
    ys = all_points_world[:,1]
    xmin, xmax = xs.min()-padding, xs.max()+padding
    ymin, ymax = ys.min()-padding, ys.max()+padding
    x_bins = int(math.ceil((xmax - xmin)/resolution))
    y_bins = int(math.ceil((ymax - ymin)/resolution))
    # histogram2d expects x,y sequences
    H, xedges, yedges = np.histogram2d(xs, ys, bins=[x_bins, y_bins], range=[[xmin, xmax],[ymin, ymax]])
    # flip for image display (so y increases upward)
    H = np.rot90(H)
    extent = [xmin, xmax, ymin, ymax]
    return H, extent

# -------------------------
# Main pipeline
# -------------------------
def main():
    print("Reading frames from:", JSON_FILE)
    frames = read_all_frames(JSON_FILE)
    keys = list(frames.keys())
    print(f"Found {len(keys)} frames in file.")

    # Preprocess scans: build list of Nx2 arrays
    scans = []
    frame_keys = []
    for i, k in enumerate(keys):
        if (i % FRAME_SUBSAMPLE) != 0:
            continue
        pts = scan_to_xy(frames[k])
        if pts.shape[0] < MIN_POINTS_PER_SCAN:
            continue
        # downsample points to speed up ICP
        pts = downsample_points(pts, POINT_SUBSAMPLE)
        scans.append(pts)
        frame_keys.append(k)

    if len(scans) < 2:
        print("Not enough scans to build map.")
        return

    # initialize pose list: start at origin
    poses_R = []
    poses_t = []
    poses_R.append(np.eye(2))
    poses_t.append(np.zeros(2))

    all_world_points = []
    all_world_points.append(transform_points(scans[0], poses_R[0], poses_t[0]))

    print("Performing pairwise ICP on", len(scans), "scans ...")
    for i in range(1, len(scans)):
        src = scans[i]        # new scan to align
        dst = scans[i-1]      # previous scan in local frame
        # Try ICP with multiple scales: first coarse (subsample), then refine
        R_rel, t_rel, err = icp_point_to_point(src, dst, max_iters=MAX_ICP_ITERS,
                                               tol=ICP_TOL, max_correspondence_dist=MAX_MATCH_DIST)
        # compose onto previous global transform
        R_prev, t_prev = poses_R[-1], poses_t[-1]
        R_new, t_new = compose_transform(R_prev, t_prev, R_rel, t_rel)
        poses_R.append(R_new)
        poses_t.append(t_new)
        # transform current scan into world
        world_pts = transform_points(src, R_new, t_new)
        all_world_points.append(world_pts)
        if (i % 10) == 0 or i == len(scans)-1:
            print(f"Scans processed: {i+1}/{len(scans)}  ICP_err={err:.3f}")

    # concat all points
    all_pts = np.vstack(all_world_points)
    print("Total accumulated points:", all_pts.shape[0])

    # Build occupancy-style grid
    print("Building occupancy grid ...")
    H, extent = build_map(all_pts, resolution=MAP_RESOLUTION, padding=MAP_PADDING)

    # Plot map and trajectory
    print("Plotting map and trajectory ...")
    fig, ax = plt.subplots(figsize=(10,10))
    im = ax.imshow(H, extent=extent, cmap="gray_r", origin="lower")
    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    ax.set_title(f"Occupancy-like map (resolution={MAP_RESOLUTION})")
    # plot trajectory (centroids of scans)
    traj = []
    for R,t in zip(poses_R, poses_t):
        # robot origin transform: apply R,t to (0,0) -> t
        traj.append(t.copy())
    traj = np.vstack(traj)
    ax.plot(traj[:,0], traj[:,1], "-r", linewidth=1.5, label="trajectory")
    ax.scatter(traj[:,0], traj[:,1], s=8, c="red")
    ax.legend()
    plt.show()

    # Optionally save map image and pointcloud
    out_img = f"map_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    fig.savefig(out_img, dpi=200)
    print("Saved map image to", out_img)

    out_pc = f"map_points_{datetime.now().strftime('%Y%m%d_%H%M%S')}.npy"
    np.save(out_pc, all_pts)
    print("Saved raw transformed points to", out_pc)


if __name__ == "__main__":
    main()
