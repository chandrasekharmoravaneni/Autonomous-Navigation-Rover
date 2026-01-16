import json
import matplotlib.pyplot as plt
import matplotlib.animation as animation

# Read JSON
with open("/Users/chandrasekharmoravaneni/autonomous_rover/lidar_20250826_192038.json") as f:
    data = json.load(f)


# Extract frames
frames = []
for key in sorted(data.keys(), key=lambda x: int(x.split("_")[1])):
    frames.append(data[key]["points"])

# Setup plot
fig, ax = plt.subplots(figsize=(7, 7))
ax.set_aspect("equal")

xs = [p[0] for p in frames[0]]
ys = [p[1] for p in frames[0]]

scatter = ax.scatter(xs, ys, s=5)

ax.set_xlim(-10000, 10000)
ax.set_ylim(-10000, 10000)

def update(i):
    pts = frames[i]
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]

    scatter.set_offsets(list(zip(xs, ys)))
    ax.set_title(f"LiDAR Frame {i+1}")
    return scatter,

ani = animation.FuncAnimation(
    fig, update, frames=len(frames), interval=100, blit=True
)

ani.save("lidar_animation_test_5_5.mp4", writer="ffmpeg", fps=10)

plt.show()
