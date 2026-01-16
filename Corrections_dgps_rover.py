import socket
from sbp.client import Handler, Framer
from sbp.table import dispatch
import time

# ---------------------------------------
# ROVER TCP CONFIG
# ---------------------------------------
ROVER_IP = "195.37.48.235"   # <-- change to your rover IP
ROVER_PORT = 55555           # <-- change to your port

print(f"Connecting to rover {ROVER_IP}:{ROVER_PORT} ...")

# ---------------------------------------
# CREATE TCP SOCKET
# ---------------------------------------
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect((ROVER_IP, ROVER_PORT))

# Use socket recv/send for SBP Framer
framer = Framer(sock.recv, sock.send)
handler = Handler(framer)

# Buffers
obs_buffer = {}
gps_time = None

print("Connected! Reading SBP stream...\n")

# ---------------------------------------
# MAIN SBP READER LOOP
# ---------------------------------------
for msg_type, msg, sender in handler:

    # dynamic decode of any SBP type
    sbp_msg = dispatch(msg_type, msg)

    msg_name = sbp_msg.__class__.__name__

    # -----------------------------------
    # TIME
    # -----------------------------------
    if msg_name == "MsgGPSTime":
        gps_time = {"tow": sbp_msg.tow, "wn": sbp_msg.wn}
        print("TIME:", gps_time)

    # -----------------------------------
    # RAW OBSERVATIONS
    # -----------------------------------
    if msg_name == "MsgObs":
        tow = sbp_msg.header.t.tow

        if tow not in obs_buffer:
            obs_buffer[tow] = []

        for o in sbp_msg.obs:
            obs_buffer[tow].append({
                "sat": o.sid.sat,
                "code": o.P,
                "carrier_phase": o.L.i + o.L.f/256,
                "doppler": o.D.i,
                "cn0": o.cn0,
                "freq_code": o.sid.code
            })

        print(f"[OBS] TOW={tow}, sats={len(sbp_msg.obs)}")

    # -----------------------------------
    # NAV POSITION
    # -----------------------------------
    if msg_name == "MsgPosLLH":
        print(f"[POS] lat={sbp_msg.lat}, lon={sbp_msg.lon}, h={sbp_msg.height}")

    # -----------------------------------
    # BASELINE (IF RTK)
    # -----------------------------------
    if msg_name == "MsgBaselineNED":
        print(f"[BASELINE] N={sbp_msg.n}  E={sbp_msg.e}  D={sbp_msg.d}")

    time.sleep(0.01)
