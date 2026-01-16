#!/usr/bin/env python3
"""
DGPS_Corrections.py
Version-safe SBP script to verify BASE DGPS correction generation
"""

from sbp.client.drivers.network_drivers import TCPDriver
from sbp.client.framer import Framer
from sbp.client.handler import Handler

from sbp.system import MsgHeartbeat
from sbp.observation import MsgObs
from sbp.navigation import MsgPosECEF

BASE_IP = "195.37.48.235"
BASE_PORT = 55555

# SBP message IDs (stable across versions)
MSG_AGE_CORRECTIONS = 0x0044
MSG_DGNSS_STATUS   = 0x0046


def handle(msg, meta):
    msg_id = msg.msg_type

    if isinstance(msg, MsgHeartbeat):
        print("✔ HEARTBEAT: base alive")

    elif isinstance(msg, MsgPosECEF):
        print(f"✔ POS ECEF: x={msg.x} y={msg.y} z={msg.z}")

    elif isinstance(msg, MsgObs):
        print(f"✔ OBSERVATIONS: {msg.n_obs}")

    elif msg_id == MSG_AGE_CORRECTIONS:
        age = getattr(msg, "age", "unknown")
        print(f"✔ AGE CORRECTIONS: {age} s")

    elif msg_id == MSG_DGNSS_STATUS:
        print("✔ DGNSS STATUS: DGPS engine active")


def main():
    print(f"\nConnecting to BASE {BASE_IP}:{BASE_PORT} via SBP...\n")

    driver = TCPDriver(BASE_IP, BASE_PORT)

    # ✅ FIX: pass read/write explicitly
    framer = Framer(driver.read, driver.write)
    handler = Handler(framer)

    handler.add_callback(handle)

    for _ in handler:
        pass


if __name__ == "__main__":
    main()
