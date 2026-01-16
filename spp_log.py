from sbp.client.drivers.network_drivers import TCPDriver
from sbp.client import Framer
from sbp.navigation import MsgPosLLH, MsgVelNED
import csv
import time
import math

IP = "195.37.48.233"
PORT = 55555

driver = TCPDriver(IP, PORT)
framer = Framer(driver.read, driver.write)

# store latest velocity
v_n = 0.0
v_e = 0.0

csv_file = open("positions_spp_speed6.csv", "w", newline="")
writer = csv.writer(csv_file)
writer.writerow([
    "timestamp",
    "lat_deg",
    "lon_deg",
    "h_accuracy_m",
    "n_sats",
    "fix",
    "speed_mps"
])

print("Logging position + speed (SPP)… Ctrl+C to stop\n")

try:
    for msg, meta in framer:

        # -------- velocity message --------
        if isinstance(msg, MsgVelNED):
            v_n = msg.n  # north velocity (m/s)
            v_e = msg.e  # east velocity (m/s)

        # -------- position message --------
        if isinstance(msg, MsgPosLLH):
            fix = msg.flags & 0x7

            speed = math.sqrt(v_n**2 + v_e**2)

            writer.writerow([
                time.time(),
                msg.lat,
                msg.lon,
                msg.h_accuracy,
                msg.n_sats,
                fix,
                speed
            ])

            print(
                f"Fix={fix} | "
                f"Hacc={msg.h_accuracy:5.2f} m | "
                f"Speed≈{speed:4.2f} m/s | "
                f"Lat={msg.lat:.8f} Lon={msg.lon:.8f}"
            )

except KeyboardInterrupt:
    print("\nStopped logging")

finally:
    csv_file.close()
    print("CSV saved: positions_spp_speed.csv")
