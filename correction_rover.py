from sbp.client.drivers.network_drivers import TCPDriver
from sbp.client import Framer
from sbp.navigation import MsgPosLLH, MsgPosLLHDepA
import csv
import time

IP = "195.37.48.235"
PORT = 55555

driver = TCPDriver(IP, PORT)
framer = Framer(driver.read, driver.write)

csv_file = open("positions7.csv", "w", newline="")
writer = csv.writer(csv_file)
writer.writerow([
    "timestamp",
    "lat_deg",
    "lon_deg",
    "height_m",
    "h_accuracy_m",
    "n_sats",
    "fix"
])

print("Logging positions... Ctrl+C to stop")

try:
    for msg, meta in framer:
        if isinstance(msg, (MsgPosLLH, MsgPosLLHDepA)):
            fix = msg.flags & 0x7

            writer.writerow([
                time.time(),
                msg.lat,
                msg.lon,
                msg.height,
                msg.h_accuracy,
                msg.n_sats,
                fix
            ])

            print(
                f"Fix={fix} | "
                f"Hacc={msg.h_accuracy:.2f} m | "
                f"Lat={msg.lat:.8f} Lon={msg.lon:.8f}"
            )

except KeyboardInterrupt:
    print("\nStopped")

finally:
    csv_file.close()
