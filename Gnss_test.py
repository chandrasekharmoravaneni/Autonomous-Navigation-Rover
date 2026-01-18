import matplotlib.pyplot as plt

from sbp.client.drivers.network_drivers import TCPDriver
from sbp.client.framer import Framer
from sbp.navigation import MsgPosLLH

ROVER_IP = "195.37.48.233"
PORT = 55555

print("Connecting to GNSS receiver...")
driver = TCPDriver(ROVER_IP, PORT)
framer = Framer(driver.read, driver.write)

lats = []
lons = []

# ======================
# MATPLOTLIB SETUP
# ======================
plt.figure()
plt.title("Live GNSS Position (SBAS)")
plt.xlabel("Longitude")
plt.ylabel("Latitude")
plt.grid(True)

line, = plt.plot([], [], "-b")

plt.show(block=False)   # 🔴 THIS IS THE KEY LINE

print("Receiving positions...\n")

# ======================
# MAIN LOOP
# ======================
for msg, meta in framer:
    if isinstance(msg, MsgPosLLH):

        lat = msg.lat
        lon = msg.lon

        print(f"Latitude: {lat:.8f}, Longitude: {lon:.8f}")

        lats.append(lat)
        lons.append(lon)

        line.set_data(lons, lats)

        plt.gca().relim()
        plt.gca().autoscale_view()

        plt.pause(0.05)   # 🔴 REQUIRED FOR GUI REFRESH
