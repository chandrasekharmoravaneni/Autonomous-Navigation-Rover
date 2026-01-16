from sbp.client import Handler
from sbp.client.drivers.network_drivers import TCPDriver
from sbp.navigation import MsgPosLLH

PIKSI_IP   = "195.37.48.235"
PIKSI_PORT = 55555

FIX_MAP = {
    0: "INVALID",
    1: "SPP (Single)",
    2: "DGPS",
    3: "RTK FLOAT",
    4: "RTK FIX"
}

def pos_cb(msg, **metadata):
    fix = FIX_MAP.get(msg.flags, "UNKNOWN")
    print(
        f"FIX: {fix:<10} | "
        f"LAT: {msg.lat:.9f} | "
        f"LON: {msg.lon:.9f} | "
        f"HGT: {msg.height:.3f}"
    )

def main():
    print(f"Connecting to Piksi Multi at {PIKSI_IP}:{PIKSI_PORT}")

    # ✅ OFFICIAL SBP TCP DRIVER
    with TCPDriver(PIKSI_IP, PIKSI_PORT) as driver:
        handler = Handler(driver.read, driver.write)
        handler.add_callback(MsgPosLLH, pos_cb)

        print("Listening for SBP data (Ctrl+C to stop)...")
        handler.start()

if __name__ == "__main__":
    main()
    try:
        while True:
            pass
    except KeyboardInterrupt:
        print("\nStopped")