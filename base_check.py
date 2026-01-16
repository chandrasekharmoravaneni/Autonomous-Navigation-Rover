# base_check.py  (SAFE FOR ALL SBP VERSIONS)

from sbp.client.drivers.network_drivers import TCPDriver
from sbp.client.framer import Framer

from sbp.observation import MsgObs
from sbp.navigation import MsgBaselineNED, MsgDops, MsgPosLLH, MsgAgeCorrections
from sbp.observation import MsgGloBiases

import datetime, time

BASE_IP = "195.37.48.235"   # <— your base IP
PORT = 55555
driver = TCPDriver(BASE_IP, PORT)
framer = Framer(driver.read, driver.write)

start = time.time()
timeout = 12

print(f"\nConnecting to BASE {BASE_IP}:{PORT} for {timeout} seconds...\n")

found = {}

for msg, meta in framer:
    name = msg.__class__.__name__
    found[name] = found.get(name, 0) + 1
    t = datetime.datetime.now().isoformat()
    print(f"[{t}] {name}")

    # Print key message info
    if isinstance(msg, MsgAgeCorrections):
        print("  → AgeCorrections:", msg.age, "seconds")

    if isinstance(msg, MsgBaselineNED):
        print("  → Baseline (mm):", msg.n, msg.e, msg.d)

    if isinstance(msg, MsgGloBiases):
        print("  → GLO Biases received")

    if isinstance(msg, MsgPosLLH):
        print("  → Base LLH:", msg.lat, msg.lon, "Flags:", msg.flags)

    # Detect DGNSS status even without import
    if name == "MsgDgnssStatus":
        print("  → DGNSS Status (present)")

    if time.time() - start > timeout:
        break

print("\n=== SUMMARY OF RECEIVED SBP MESSAGES (BASE) ===")
for k,v in found.items():
    print(f"{k:20s} : {v} messages")
