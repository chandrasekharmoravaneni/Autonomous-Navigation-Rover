from sbp.client.drivers.network_drivers import TCPDriver
from sbp.client import Handler, Framer

from sbp.navigation import (
    SBP_MSG_POS_LLH,
    SBP_MSG_POS_ECEF
)

from sbp.observation import (
    SBP_MSG_OBS,
    SBP_MSG_BASE_POS_LLH,
    SBP_MSG_BASE_POS_ECEF
)

BASE_IP = "195.37.48.235"
PORT = 55555  # SBP port (tcp.server0)

print("Connecting to base using SBP...\n")

# ---------------- Callbacks ----------------

def base_position_cb(msg, **metadata):
    print("✔ Base FIXED position message received")

def observation_cb(msg, **metadata):
    print("✔ GNSS observations generated (base active)")

def position_cb(msg, **metadata):
    if msg.flags & 0x02:
        print("✔ Corrections possible (DGNSS / RTK capable)")
    else:
        print("ℹ Standalone position")

# ---------------- Connection ----------------

with TCPDriver(BASE_IP, PORT) as driver:
    framer = Framer(driver.read, driver.write)
    handler = Handler(framer)

    handler.add_callback(base_position_cb, SBP_MSG_BASE_POS_LLH)
    handler.add_callback(base_position_cb, SBP_MSG_BASE_POS_ECEF)
    handler.add_callback(observation_cb, SBP_MSG_OBS)
    handler.add_callback(position_cb, SBP_MSG_POS_LLH)
    handler.add_callback(position_cb, SBP_MSG_POS_ECEF)

    print("Listening for SBP messages...\n")

    # ✅ THIS IS THE CORRECT CALL
    handler.start()
