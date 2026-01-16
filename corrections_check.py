from sbp.client.drivers.network_drivers import TCPDriver
from sbp.client import Framer

from sbp.navigation import MsgPosLLH, MsgPosLLHDepA
from sbp.observation import MsgObs

BASE_IP = "195.37.48.233"   # <-- BASE IP HERE
BASE_PORT = 55555             # usually same SBP port

driver = TCPDriver(BASE_IP, BASE_PORT)
framer = Framer(driver.read, driver.write)

obs_seen = False

print("\n--- Monitoring ROVER status ---\n")

for msg, meta in framer:

    # --------- Base observations ---------
    '''if isinstance(msg, MsgObs):
        obs_seen = True
        print("✔ Base is outputting SBP observations")'''

    # --------- Base position & fix ---------
    if isinstance(msg, (MsgPosLLH, MsgPosLLHDepA)):
        fix = msg.flags & 0x7

        fix_map = {
            0: "No Fix",
            1: "SPP",
            2: "DGPS",
            3: "RTK Float",
            4: "RTK Fixed",
            5: "Dead Reckoning",
            6: "INS + GNSS",
        }

        print(
            f"📡 Base Fix={fix_map.get(fix, fix)} | "
            f"Sats={msg.n_sats} | "
            f"H_acc={msg.h_accuracy:.3f} m | "
            f"Lat={msg.lat:.8f} Lon={msg.lon:.8f} H={msg.height:.3f}"
        )

        # --------- Base sanity check ---------
        #if msg.h_accuracy < 0.05:
            #print("\n✔ BASE POSITION IS FIXED & HIGH QUALITY")
            #break
        #elif msg.h_accuracy > 1.0:
            #print("⚠ Base position NOT fixed (surveying or unstable)")
