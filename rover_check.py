# rover_check.py
from sbp.client.drivers.network_drivers import TCPDriver
from sbp.client.framer import Framer
from sbp.navigation import MsgPosLLH, MsgBaselineNED, MsgDops, MsgAgeCorrections
import datetime, time

ROVER_IP = "195.37.48.233"   # <-- replace with rover IP
PORT = 55555
driver = TCPDriver(ROVER_IP, PORT)
framer = Framer(driver.read, driver.write)

start = time.time()
timeout = 12
print(f"Connecting to rover {ROVER_IP}:{PORT} for {timeout}s...\n")

for msg, meta in framer:
    name = msg.__class__.__name__
    t = datetime.datetime.now().isoformat()
    print(f"[{t}] {name}")

    if isinstance(msg, MsgPosLLH):
        flags = msg.flags & 0x07
        print("  -> PosLLH flags:", msg.flags, "interp:", flags, " (0=no fix,1=SPP,2=DGPS,4=RTK FLOAT,5=RTK FIX)")
    if isinstance(msg, MsgBaselineNED):
        print("  -> Baseline (mm):", msg.n, msg.e, msg.d)
    if isinstance(msg, MsgDops):
        print("  -> HDOP/VDOP:", msg.hdop/10.0, msg.vdop/10.0)
    if isinstance(msg, MsgAgeCorrections):
        print("  -> AgeCorrections (s):", getattr(msg, "age", None))

    if time.time() - start > timeout:
        break
