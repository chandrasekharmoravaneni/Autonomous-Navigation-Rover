from sbp.client.drivers.network_drivers import TCPDriver
from sbp.client import Framer

from sbp.navigation import MsgAgeCorrections, MsgPosLLH
from sbp.observation import MsgObs

ROVER_IP = "195.37.48.233"
ROVER_PORT = 55555

print("Connecting to rover...")

# ✅ CORRECT for your SBP version
driver = TCPDriver(ROVER_IP, ROVER_PORT)
framer = Framer(driver.read, driver.write)

last_age = None
saw_sbp_corr = False
saw_rtcm = False

print("\n--- Detecting correction type ---\n")

for msg, meta in framer:

    # --------------------------
    # SBP correction age (authoritative)
    # --------------------------
    if isinstance(msg, MsgAgeCorrections):
        last_age = msg.age
        if last_age != 65535 and not saw_sbp_corr:
            print(f"✔ SBP corrections detected (age={last_age}s)")
            saw_sbp_corr = True

    # --------------------------
    # RTCM detection via passthrough IDs
    # --------------------------
    # msg_type is numeric SBP message ID
    msg_id = getattr(msg, "msg_type", None)
    if msg_id is not None and msg_id >= 0xF000:
        if not saw_rtcm:
            print("✔ RTCM corrections detected (SBP passthrough)")
            saw_rtcm = True

    # --------------------------
    # Informational only
    # --------------------------
    if isinstance(msg, MsgObs):
        pass

    # --------------------------
    # Stop once identified
    # --------------------------
    if saw_sbp_corr or saw_rtcm:
        print("\n--- SUMMARY ---")
        if saw_sbp_corr:
            print("✔ Base is sending SBP corrections")
        if saw_rtcm:
            print("✔ Base is sending RTCM corrections")
        break
