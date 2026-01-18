import json
import signal
import sys

from sbp.observation import (
    MsgObs,
    MsgEphemerisGPS,
    MsgEphemerisGlo,
    MsgEphemerisGal,
    MsgEphemerisBds,
    MsgEphemerisQzss,
    MsgEphemerisSbas
)

from sbp.navigation import MsgPosLLH
from sbp.client.drivers.network_drivers import TCPDriver
from sbp.client.framer import Framer


BASE_IP = "195.37.48.235"
BASE_PORT = 55555

OBS_LOG_FILE = "obs2_log.json"
EPH_LOG_FILE = "eph_log1.json"


# --------------------------
# Graceful Exit (CTRL + C)
# --------------------------
def handle_sigint(signum, frame):
    print("\n  Stopping SBP receiver... (Ctrl+C pressed)")
    sys.exit(0)

signal.signal(signal.SIGINT, handle_sigint)


# --------------------------
# Save OBS JSON
# --------------------------
def save_obs_json(msg):
    obs_list = []

    for o in msg.obs:
        obs_list.append({
            "P": o.P,
            "L_i": o.L.i,
            "L_f": o.L.f,
            "cn0": o.cn0,
            "lock": o.lock,
            "sid": {
                "sat": o.sid.sat,
                "code": o.sid.code
            }
        })

    data = {
        "type": "obs",
        "tow": msg.header.t.tow,
        "wn": msg.header.t.wn,
        "n_obs": msg.header.n_obs,
        "obs": obs_list
    }

    with open(OBS_LOG_FILE, "a") as f:
        f.write(json.dumps(data) + "\n")


# --------------------------
# Save EPHEMERIS JSON
# --------------------------
def save_eph_json(msg):
    # Convert message to dict using SBP built-in to_json_dict()
    try:
        data = msg.to_json_dict()
    except:
        # fallback simple conversion
        data = msg.__dict__

    with open(EPH_LOG_FILE, "a") as f:
        f.write(json.dumps(data) + "\n")


# --------------------------
# Main Receiver
# --------------------------
def main():
    print("Connecting to base SBP stream...")
    driver = TCPDriver(BASE_IP, BASE_PORT)
    framer = Framer(driver.read, None)

    print("Connected.")
    print("Listening for MsgObs + MsgPosLLH + Ephemeris (Ctrl+C to stop)...\n")

    for msg, _ in framer:

        # --------- OBS MESSAGES ----------
        if isinstance(msg, MsgObs):
            print("✔ MsgObs — Observation correction")
            print(f"  Number of Obs: {len(msg.obs)}")
            print(f"  Tow: {msg.header.t.tow}\n")
            save_obs_json(msg)

        # --------- BASE POSITION ----------
        elif isinstance(msg, MsgPosLLH):
            print("✔ MsgPosLLH — Base Position")
            print(f"  Lat: {msg.lat}")
            print(f"  Lon: {msg.lon}")
            print(f"  Hgt: {msg.height}\n")

        # --------- EPHEMERIS MESSAGES ----------
        elif isinstance(msg, MsgEphemerisGPS):
            print("✔ GPS Ephemeris received")
            save_eph_json(msg)

        elif isinstance(msg, MsgEphemerisGlo):
            print("✔ GLONASS Ephemeris received")
            save_eph_json(msg)

        elif isinstance(msg, MsgEphemerisGal):
            print("✔ Galileo Ephemeris received")
            save_eph_json(msg)

        elif isinstance(msg, MsgEphemerisBds):
            print("✔ BeiDou Ephemeris received")
            save_eph_json(msg)

        elif isinstance(msg, MsgEphemerisQzss):
            print("✔ QZSS Ephemeris received")
            save_eph_json(msg)

        elif isinstance(msg, MsgEphemerisSbas):
            print("✔ SBAS Ephemeris received")
            save_eph_json(msg)


if __name__ == "__main__":
    main()
