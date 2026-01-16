import json
import matplotlib.pyplot as plt
import matplotlib.animation as animation

with open("lidar_tim781_1.json") as f:
    data = json.load(f)

frames = []
for key in sorted(data.keys(), key=lambda x: int(x.split("_")[1])):
    frame_points = data[key]
    xs = [p["x"] for p in frame_points]
    ys = [p["y"] for p in frame_points]
    frames.append((xs, ys))

fig, ax = plt.subplots(figsize=(7, 7))
ax.set_aspect("equal")

def update(i):
    ax.clear()
    xs, ys = frames[i]
    ax.scatter(xs, ys, s=5)
    ax.set_xlim(-5000, 5000)
    ax.set_ylim(-5000, 5000)
    ax.set_aspect("equal")
    ax.set_title(f"LiDAR Frame {i+1}")

ani = animation.FuncAnimation(fig, update, frames=len(frames), interval=120)

# ---- SAVE AS MP4 ----
ani.save("lidar_animation_test_1.mp4", writer="ffmpeg", fps=15)

# ---- SAVE AS GIF ----
# ani.save("lidar_animation.gif", writer="pillow", fps=10)

plt.show()
