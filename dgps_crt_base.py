from sbp.client.drivers.network_drivers import TCPDriver
from sbp.client.framer import Framer

from sbp.observation import MsgObs
from sbp.navigation import MsgBaselineNED
from sbp.navigation import MsgPosLLH
from sbp.navigation import MsgDops

BASE_IP = "195.37.48.235"   # BASE station IP
PORT = 55555                # SBP port

driver = TCPDriver(BASE_IP, PORT)
framer = Framer(driver.read, driver.write)

print("Checking for SBP corrections from BASE...\n")

for msg, meta in framer:

    if isinstance(msg, MsgObs):
        print("✔ SBP OBS received — BASE is sending corrections!")
    
    if isinstance(msg, MsgBaselineNED):
        print("✔ RTK Baseline received — Rover is solving RTK")
        print("   Baseline N,E,D (m):", msg.n/1000, msg.e/1000, msg.d/1000)

    if isinstance(msg, MsgPosLLH):
        print("Rover Position:", msg.lat, msg.lon)

    if isinstance(msg, MsgDops):
        print("DOP:", msg.hdop/10, msg.vdop/10)
