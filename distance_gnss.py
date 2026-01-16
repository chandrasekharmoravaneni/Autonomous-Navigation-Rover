import math
from sbp.client.drivers.network_drivers import TCPDriver
from sbp.client import Handler, Framer
from sbp.navigation import SBP_MSG_POS_ECEF

PIKSI_IP = "195.37.48.233"
PIKSI_PORT = 55555

prev_x = None
prev_y = None
prev_z = None

total_distance = 0.0  # meters

def ecef_distance(x1, y1, z1, x2, y2, z2):
    return math.sqrt(
        (x2 - x1)**2 +
        (y2 - y1)**2 +
        (z2 - z1)**2
    )

with TCPDriver(PIKSI_IP, PIKSI_PORT) as driver:
    with Handler(driver.read, driver.write) as handler:
        with Handler(Framer(driver.read, None)) as source:

            for msg, metadata in source.filter(SBP_MSG_POS_ECEF):

                # Ignore invalid fixes
                if msg.flags == 0:
                    continue

                x = msg.x
                y = msg.y
                z = msg.z

                if prev_x is not None:
                    d = ecef_distance(prev_x, prev_y, prev_z, x, y, z)

                    # Filter GNSS noise when stationary
                    if d > 0.05:   # 5 cm threshold
                        total_distance += d

                    print(f"Step distance : {d:.3f} m")
                    print(f"Total distance: {total_distance:.3f} m")

                prev_x = x
                prev_y = y
                prev_z = z
