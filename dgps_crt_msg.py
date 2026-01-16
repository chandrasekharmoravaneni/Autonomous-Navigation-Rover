from sbp.client.drivers.network_drivers import TCPDriver
from sbp.client.framer import Framer

from sbp.observation import MsgObs
from sbp.navigation import MsgBaselineNED, MsgPosLLH, MsgDops

ROVER_IP = "195.37.48.233"
PORT = 55555

print("Connecting to rover...")
driver = TCPDriver(ROVER_IP, PORT)
framer = Framer(driver.read, driver.write)

print("Listening for SBP messages...\n")

got_obs = False
got_baseline = False

for msg, meta in framer:

    # 🔍 DEBUG: show every message type received
    print("RX:", type(msg).__name__)

    # 🛰️ RAW GNSS OBSERVATIONS (DGPS / RTK)
    if isinstance(msg, MsgObs):
        got_obs = True
        print("\n✔ DGPS / RTK OBSERVATIONS RECEIVED")
        print(f"  TOW: {msg.header.t.tow}")
        print(f"  Satellites: {len(msg.obs)}")

        for o in msg.obs:
            print(
                f"   SAT={o.sid.sat:02d} "
                f"PR={o.P:10.3f} "
                f"CP={o.L.i:10d} "
                f"DOP={o.D.i:6d}"
            )

    # 📐 RTK BASELINE (strong RTK indicator)
    elif isinstance(msg, MsgBaselineNED):
        got_baseline = True
        print("\n✔ RTK BASELINE RECEIVED")
        print(
            f"   N={msg.n/1000:.3f} m  "
            f"E={msg.e/1000:.3f} m  "
            f"D={msg.d/1000:.3f} m"
        )

    # 📍 POSITION SOLUTION
    elif isinstance(msg, MsgPosLLH):
        print("\n📍 POSITION")
        print(
            f"   Lat={msg.lat:.8f}  "
            f"Lon={msg.lon:.8f}  "
            f"H={msg.height:.2f} m"
        )

    # 📊 DOP VALUES
    elif isinstance(msg, MsgDops):
        print("\n📊 DOPS")
        print(
            f"   GDOP={msg.gdop/100:.2f} "
            f"PDOP={msg.pdop/100:.2f} "
            f"HDOP={msg.hdop/100:.2f}"
        )

    # 🎉 CONFIRM DGPS / RTK
    if got_baseline or got_obs:
        print("\n🎉 DGPS / RTK IS ACTIVE\n")
