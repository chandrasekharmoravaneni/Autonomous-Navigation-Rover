# save as sbp_base_check.py
from sbp.client.drivers.network_drivers import TCPDriver
from sbp.client.framer import Framer
import datetime

BASE_IP = "195.37.48.235"   # set to your BASE IP
PORT = 55555
driver = TCPDriver(BASE_IP, PORT)
framer = Framer(driver.read, driver.write)

REQUIRED = {
    "MsgBasePosLLH": False,
    "MsgObs": False,
    "MsgEphemerisGPS": False,
    "MsgEphemerisGLO": False,
    "MsgGloBiases": False,
    "MsgIono": False,
    "MsgOrbitClock": False
}

print(f"Connecting to base {BASE_IP}:{PORT} ...\nCollecting messages for 15 seconds...\n")

start = datetime.datetime.now()
timeout = 15  # seconds
for msg, meta in framer:
    name = msg.__class__.__name__
    sender = getattr(meta, "sender", None)
    print(f"[{datetime.datetime.now().isoformat()}] {name}  (sender={sender})")
    if name in REQUIRED:
        REQUIRED[name] = True

    # stop after timeout
    if (datetime.datetime.now() - start).total_seconds() > timeout:
        break

print("\n=== Summary of required RTK SBP messages ===")
for k, v in REQUIRED.items():
    print(f"{k:20s} : {'PRESENT' if v else 'MISSING'}")
