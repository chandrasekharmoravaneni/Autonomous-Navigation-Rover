from sbp.client.drivers.network_drivers import TCPDriver
from sbp.client import Framer

from sbp.observation import MsgObs
from sbp.navigation import MsgPosLLH

ROVER_IP = "195.37.48.233"   # ROVER IP
PORT = 55555

driver = TCPDriver(ROVER_IP, PORT)
framer = Framer(driver.read, driver.write)

fix_map = {
    0: "NO FIX",
    1: "SPP (Standalone / SBAS)",
    2: "DGPS ✅",
    3: "RTK FLOAT",
    4: "RTK FIXED",
    5: "DR",
    6: "INS + GNSS"
}

obs_seen = False

print("\n--- DGPS STATUS CHECK (ROVER) ---\n")

for msg, meta in framer:

    # 1️⃣ Check if rover receives base observations
    if isinstance(msg, MsgObs) and not obs_seen:
        obs_seen = True
        print("✔ Rover IS receiving SBP observations from base")

    # 2️⃣ Check navigation fix
    if isinstance(msg, MsgPosLLH):
        fix = msg.flags & 0x7

        print(
            f"\n📡 FIX TYPE : {fix_map.get(fix, fix)}\n"
            f"🛰  Satellites : {msg.n_sats}\n"
            f"📏 H Accuracy : {msg.h_accuracy:.3f} m\n"
            f"📍 Lat/Lon   : {msg.lat:.8f}, {msg.lon:.8f}\n"
        )

        # Final verdict
        if fix == 2:
            print("🎯 DGPS IS ACTIVE AND CORRECTIONS ARE APPLIED\n")
        elif fix == 1:
            print("⚠ DGPS NOT ACTIVE (SPP / SBAS)\n")
            print("➡ Disable SBAS and ensure base is FIXED\n")
        else:
            print("ℹ Fix mode:", fix_map.get(fix, fix), "\n")
