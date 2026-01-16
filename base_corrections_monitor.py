#!/usr/bin/env python3

from sbp.client.drivers.network_drivers import TCPDriver
from sbp.client.framer import Framer
from sbp.observation import MsgObs

BASE_IP = "195.37.48.235"   # your base IP
PORT    = 55555             # your base TCP port

print("\nChecking if BASE is sending raw RTK corrections (MsgObs)...\n")

driver = TCPDriver(BASE_IP, PORT)
framer = Framer(driver.read, driver.write)

obs_count = 0

try:
    for msg, meta in framer:

        if isinstance(msg, MsgObs):
            obs_count += 1
            tow = msg.header.t.tow
            n   = msg.header.n_obs
            print(f"✔ MsgObs received → tow={tow}, n_obs={n}")

            if obs_count >= 5:
                print("\n🎉 RESULT: BASE **IS SENDING** RAW GNSS CORRECTIONS (MsgObs)")
                break

except KeyboardInterrupt:
    pass

if obs_count == 0:
    print("\n❌ RESULT: BASE IS **NOT SENDING** RTK MsgObs corrections.")
