from sbp.client.drivers.network_drivers import TCPDriver
from sbp.client import Framer

from sbp.navigation import MsgPosLLH, MsgAgeCorrections
from sbp.observation import MsgObs

ROVER_IP = "195.37.48.235"
ROVER_PORT = 55555

print("Connecting to rover SBP:", ROVER_IP, ROVER_PORT)
driver = TCPDriver(ROVER_IP, ROVER_PORT)
framer = Framer(driver.read, driver.write)

got_obs = False
got_base_pos = False
got_age = False
last_age = None

print("\nChecking for SBP corrections...\n")

for msg, meta in framer:

    # --------------------------
    # CHECK 1: OBS messages
    # --------------------------
    if isinstance(msg, MsgObs):
        if not got_obs:
            print("✔ Rover receiving MsgObs (base satellite observations)")
            got_obs = True

    # --------------------------
    # CHECK 2: Base position
    # --------------------------
    if msg.__class__.__name__ in ("MsgBasePosLLH", "MsgBasePosECEF"):
        if not got_base_pos:
            print(f"✔ Rover received Base Position: {msg}")
            got_base_pos = True

    # --------------------------
    # CHECK 3: Correction Age
    # --------------------------
    if isinstance(msg, MsgAgeCorrections):
        last_age = msg.age
        if last_age == 65535:
            print("✖ No valid corrections yet (age=65535)")
        else:
            if not got_age:
                print(f"✔ Correction age OK: {last_age} sec")
                got_age = True

    # --------------------------
    # CHECK 4: Position flags (solution type)
    # --------------------------
    if isinstance(msg, MsgPosLLH):
        flags = msg.flags
        hacc = msg.h_accuracy
        sats = msg.n_sats

        print(f"POS: LAT={msg.lat:.8f}, LON={msg.lon:.8f}, FLAGS={flags}, SATS={sats}, HACC={hacc}cm")

        if flags == 6 and last_age not in (None, 65535):
            print("✔ DGPS ACTIVE (corrections applied)")
        elif flags == 6:
            print("⚠ FLAGS say DGNSS but no valid corrections received → FIX your base")
        else:
            print("✖ DGPS NOT ACTIVE")

        print("---------------------------------------")
