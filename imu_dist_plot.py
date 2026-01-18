from sbp.client.drivers.network_drivers import TCPDriver
from sbp.client import Handler
from sbp.navigation import MsgBaselineNED
import time

ROVER_IP = "195.37.48.233"
ROVER_PORT = 55555

def baseline_cb(msg, **metadata):
    east = msg.e
    north = msg.n
    up = -msg.d   # NED → ENU
    print(f"ENU: E={east:.3f} m, N={north:.3f} m, U={up:.3f} m")

print("Connecting to rover...")

with TCPDriver(ROVER_IP, ROVER_PORT) as driver:
    handler = Handler(driver.read, driver.write)

    handler.add_callback(MsgBaselineNED, baseline_cb)

    handler.start()   # ✅ start ONCE

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopped")
