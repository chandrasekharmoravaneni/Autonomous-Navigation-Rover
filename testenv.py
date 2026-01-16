
import sys
print(f"\n✅ Python version: {sys.version}\n")

# --- Core scientific stack ---
import numpy as np, scipy, pandas as pd, matplotlib.pyplot as plt
print("✅ Core libraries OK (numpy, scipy, pandas, matplotlib)")

# --- Geometry / ML / Vision ---
import shapely, sklearn, cv2
print("✅ Geometry / ML / Vision OK (shapely, scikit-learn, opencv-python)")

# --- Point clouds / 3D ---
try:
    import open3d as o3d
    print(f"✅ Open3D OK (version {o3d.__version__})")
except Exception as e:
    print("⚠️  Open3D not available:", e)

# --- Sensor Fusion / Filtering ---
import filterpy
from pyquaternion import Quaternion
print("✅ Sensor fusion libs OK (filterpy, pyquaternion)")

# --- GPS / GNSS ---
import geographiclib
import pynmeagps, pyubx2
print("✅ GPS libraries OK (geographiclib, pynmeagps, pyubx2)")

# --- Communication / System ---
import serial, usb, zmq
print("✅ Communication libs OK (pyserial, pyusb, pyzmq)")

# --- Mapping / Planning ---
import networkx, numba
print("✅ Mapping / Planning libs OK (networkx, numba)")

# --- Visualization / Simulation ---
import plotly, pygame
print("✅ Visualization libs OK (plotly, pygame)\n")

# --- Small runtime demos ---
# 1. Simple numpy/scipy demo
a = np.linspace(0, 2*np.pi, 5)
print("Sine values:", np.round(np.sin(a), 3))

# 2. Simple quaternion rotation demo
q = Quaternion(axis=[0, 0, 1], angle=np.pi/4)
rotated = q.rotate([1, 0, 0])
print("Quaternion rotation 45° around Z-axis:", np.round(rotated, 3))

# 3. OpenCV test image
img = np.zeros((100,100,3), np.uint8)
cv2.line(img, (10,10), (90,90), (0,255,0), 2)
cv2.imwrite("opencv_test.png", img)
print("OpenCV test image written: opencv_test.png")

# 4. Optional: simple matplotlib plot
plt.plot([0,1,2], [0,1,4])
plt.title("Matplotlib check")
plt.savefig("matplotlib_test.png")
print("Matplotlib test image written: matplotlib_test.png")

print("\n🎉 All checks completed. Your Python environment is ready for LiDAR + DGPS/INS development!\n")
