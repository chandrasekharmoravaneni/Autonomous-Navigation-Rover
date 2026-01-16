from sbp.client.drivers.network_drivers import TCPDriver
from sbp.client.framer import Framer

from sbp.observation import MsgObs
from sbp.navigation import MsgBaselineNED
from sbp.navigation import MsgDops
from sbp.navigation import MsgPosLLH

BASE_IP = "195.37.48.235"
PORT    = 55555

driver = TCPDriver(BASE_IP, PORT)
framer = Framer(driver.read, driver.write)

print("Listening for SBP RTK corrections...\n")

for msg, meta in framer:

    if isinstance(msg, MsgObs):
        print("✔ Received SBP OBS (GNSS raw corrections)")
        continue

    if isinstance(msg, MsgBaselineNED):
        print("✔ Received BASELINE (RTK vector) — Rover is solving RTK")
        print("   N, E, D:", msg.n/1000.0, msg.e/1000.0, msg.d/1000.0)
        continue
    
    if isinstance(msg, MsgDops):
        print("DOPS:", msg.hdop/10, msg.vdop/10)
        continue
    
    if isinstance(msg, MsgPosLLH):
        print("GNSS Position:", msg.lat, msg.lon)
        continue
