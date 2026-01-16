from sbp.client.drivers.network_drivers import TCPDriver
from sbp.client import Handler
from sbp.navigation import MsgPosLLH, MsgPosLLHCov
import time

ROVER_IP = "195.37.48.233"
ROVER_PORT = 55555

fix_map = {
    0: "INVALID",
    1: "SINGLE",
    2: "DGPS",
    3: "RTK FLOAT",
    4: "RTK FIX"
}

def pos_llh_cb(msg, **metadata):
    print(
        f"LLH: lat={msg.lat:.8f}, lon={msg.lon:.8f}, h={msg.height:.3f} | "
        f"FIX={fix_map.get(msg.flags, 'UNKNOWN')}"
    )

def pos_cov_cb(msg, **metadata):
    print(f"Corrections age: {msg.corrections_age} s")
    print("-" * 60)

print("Connecting to rover...")

with TCPDriver(ROVER_IP, ROVER_PORT) as driver:
    handler = Handler(driver.read, driver.write)

    handler.add_callback(MsgPosLLH, pos_llh_cb)
    handler.add_callback(MsgPosLLHCov, pos_cov_cb)

    handler.start()   # ✅ start ONCE

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopped")