#!/usr/bin/env python3
"""
plot_tim781.py

Usage:
  python plot_tim781.py [file.json] [--frame N] [--animate] [--save out.png]

Features:
 - auto-detects a few JSON layouts (frame_x dict or frames list).
 - plots overlay of all points (default).
 - can plot single frame: --frame 3
 - can animate frames: --animate
 - can save a static overlay PNG: --save out.png
"""
import json, sys, math, argparse, os
import matplotlib.pyplot as plt
from matplotlib import animation

DEFAULT_FILE = "./tim7xx_frames_20250826_200437.json"

def load_json(path):
    with open(path, "r") as f:
        return json.load(f)

def normalize_frames(data):
    """
    Convert known file forms into a list of frames:
    - returns list_of_frames where each frame is dict: {"timestamp": ..., "points": [ {x,y,angle,...}, ... ]}
    """
    if isinstance(data, dict):
        # case 1: {"frame_1": [...], "frame_2": [...]}
        keys = sorted([k for k in data.keys() if k.lower().startswith("frame_")],
                      key=lambda kk: int(kk.split("_",1)[1]) if "_" in kk else kk)
        if keys:
            frames = []
            for k in keys:
                frames.append({"timestamp": None, "points": data[k]})
            return frames
        # case 2: {"created":..., "frames":[ ... ]} (uploaded example)
        if "frames" in data and isinstance(data["frames"], list):
            frames = []
            for fr in data["frames"]:
                # some formats: frame entry has "points" list
                if "points" in fr:
                    frames.append({"timestamp": fr.get("timestamp"), "points": fr["points"]})
                # or the frame may already be a list (rare)
                elif isinstance(fr, list):
                    frames.append({"timestamp": None, "points": fr})
                else:
                    # fallback: try to collect x/y in keys
                    frames.append({"timestamp": fr.get("timestamp"), "points": fr.get("points", [])})
            return frames
    # fallback: if top-level is list of frames
    if isinstance(data, list):
        out = []
        for fr in data:
            if isinstance(fr, dict) and "points" in fr:
                out.append({"timestamp": fr.get("timestamp"), "points": fr["points"]})
            else:
                out.append({"timestamp": None, "points": fr})
        return out
    raise ValueError("Unknown JSON structure for frames")

def extract_xy_from_point(pt):
    """Return (x,y) or (None,None) if missing. Accepts different key names."""
    # direct x,y
    if pt is None:
        return (None, None)
    if "x" in pt and "y" in pt:
        x = pt["x"]; y = pt["y"]
        # some files use extremely small floats or nulls; filter null
        if x is None or y is None:
            return (None, None)
        return (float(x), float(y))
    # maybe stored as meters or mm with angle+distance keys
    if "angle" in pt and ("range" in pt or "range_m" in pt or "distance_mm" in pt):
        ang = float(pt["angle"])
        if "range_m" in pt:
            r = float(pt["range_m"])
        elif "range" in pt:
            r = float(pt["range"])
        else:
            # distance_mm -> convert to meters
            try:
                r = float(pt.get("distance_mm", 0)) / 1000.0
            except:
                r = 0.0
        x = r * math.cos(math.radians(ang))
        y = r * math.sin(math.radians(ang))
        return (x, y)
    # angle_deg + distance_mm
    if "angle_deg" in pt and "distance_mm" in pt:
        try:
            a = float(pt["angle_deg"])
            r = float(pt["distance_mm"]) / 1000.0
            return (r * math.cos(math.radians(a)), r * math.sin(math.radians(a)))
        except Exception:
            return (None, None)
    return (None, None)

def build_xy_lists(frames, skip_none=True):
    """
    Returns:
      all_x, all_y : lists concatenating all frames
      per_frame_xy : list of (xs, ys) per frame
    """
    all_x = []
    all_y = []
    per_frame = []
    for fr in frames:
        xs=[]; ys=[]
        for pt in fr["points"]:
            x,y = extract_xy_from_point(pt)
            if x is None or y is None:
                if not skip_none:
                    xs.append(0.0); ys.append(0.0)
                else:
                    continue
            else:
                xs.append(x); ys.append(y)
                all_x.append(x); all_y.append(y)
        per_frame.append((xs, ys))
    return all_x, all_y, per_frame

def plot_overlay(all_x, all_y, outpath=None):
    plt.figure(figsize=(8,8))
    plt.scatter(all_x, all_y, s=1, alpha=0.6)
    plt.gca().set_aspect('equal', 'box')
    plt.xlabel("X (m)")
    plt.ylabel("Y (m)")
    plt.title("Overlay: all frames")
    if outpath:
        plt.savefig(outpath, dpi=200, bbox_inches='tight')
    plt.show()

def plot_single(xs, ys, title=None, outpath=None):
    plt.figure(figsize=(7,7))
    plt.scatter(xs, ys, s=4, alpha=0.8)
    plt.gca().set_aspect('equal', 'box')
    if title:
        plt.title(title)
    if outpath:
        plt.savefig(outpath, dpi=200, bbox_inches='tight')
    plt.show()

def animate_frames(per_frame, interval=100):
    fig, ax = plt.subplots(figsize=(7,7))
    scat = ax.scatter([], [], s=4)
    ax.set_aspect('equal', 'box')
    ax.set_xlim(-10, 10)
    ax.set_ylim(-10, 10)
    ax.set_xlabel("X (m)")
    ax.set_ylabel("Y (m)")

    # compute global bounds to set axis
    xs_all = [x for (xs,ys) in per_frame for x in xs]
    ys_all = [y for (xs,ys) in per_frame for y in ys]
    if xs_all and ys_all:
        pad = 0.1
        xmin, xmax = min(xs_all), max(xs_all)
        ymin, ymax = min(ys_all), max(ys_all)
        dx = xmax - xmin; dy = ymax - ymin
        if dx == 0: dx = 1.0
        if dy == 0: dy = 1.0
        ax.set_xlim(xmin - pad*dx, xmax + pad*dx)
        ax.set_ylim(ymin - pad*dy, ymax + pad*dy)

    def init():
        scat.set_offsets([])
        return (scat,)

    def update(i):
        xs, ys = per_frame[i]
        pts = list(zip(xs, ys))
        scat.set_offsets(pts)
        ax.set_title(f"Frame {i+1} / {len(per_frame)}")
        return (scat,)

    ani = animation.FuncAnimation(fig, update, frames=len(per_frame), init_func=init,
                                  blit=True, interval=interval, repeat=True)
    plt.show()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file", nargs="?", default=DEFAULT_FILE, help="path to JSON file")
    ap.add_argument("--frame", type=int, default=None, help="plot single frame index (1-based)")
    ap.add_argument("--animate", action="store_true", help="animate frames")
    ap.add_argument("--save", type=str, default=None, help="save static overlay PNG")
    args = ap.parse_args()

    if not os.path.exists(args.file):
        print("File not found:", args.file)
        return

    data = load_json(args.file)
    frames = normalize_frames(data)
    if not frames:
        print("No frames detected in file.")
        return

    all_x, all_y, per_frame = build_xy_lists(frames, skip_none=True)

    if args.frame is not None:
        idx = max(1, args.frame) - 1
        if idx < 0 or idx >= len(per_frame):
            print("Frame index out of range (1..{})".format(len(per_frame)))
            return
        xs, ys = per_frame[idx]
        title = f"Frame {idx+1} (timestamp={frames[idx].get('timestamp')})"
        plot_single(xs, ys, title=title, outpath=args.save)
        return

    if args.animate:
        animate_frames(per_frame)
        return

    # default: overlay all points
    plot_overlay(all_x, all_y, outpath=args.save)

if __name__ == "__main__":
    main()
