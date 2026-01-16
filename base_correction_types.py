#!/usr/bin/env python3
import socket
import struct
from sbp.client import Handler, Framer
from sbp.client.drivers.network_drivers import TCPDriver
from sbp.observation import MsgObs
#from sbp.navigation import MsgBasePosLlh, MsgBasePosEcef
from sbp.observation import (
    MsgEphemerisGPS,
    MsgEphemerisGlo,
    MsgEphemerisGal,
    MsgEphemerisBds,
)

IP = "195.37.48.235"
PORT = 55555

print(f"Connecting to {IP}:{PORT} ...")
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect((IP, PORT))

sock.settimeout(0.5)

print("Connected.\nStarting auto-detect of SBP and RTCM...\n")

driver = TCPDriver(sock)
framer = Framer(driver.read, driver.write)
handler = Handler(framer)

def find_rtcm(data):
    msgs = []
    i = 0
    while i < len(data) - 3:
        if data[i] == 0xD3:  # RTCM header
            length = ((data[i+1] & 0x03) << 8) | data[i+2]
            end = i + 3 + length
            if end <= len(data):
                msgs.append(data[i:end])
                i = end
            else:
                break
        else:
            i += 1
    return msgs

print("Waiting for incoming data...\n")

while True:
    try:
        data = sock.recv(4096)
        if not data:
            continue

        # ---------- RTCM DETECTION ----------
        rtcm_msgs = find_rtcm(data)
        for m in rtcm_msgs:
            payload = m[3:]
            msg_type = (payload[0] << 4) | (payload[1] >> 4)
            print(f"[RTCM] Message type {msg_type}")

        # ---------- SBP DETECTION ----------
        try:
            for msg, md in handler:
                if isinstance(msg, MsgObs):
                    print("[SBP] MSG_OBS received")

                #elif isinstance(msg, MsgBasePosLlh):
                #    print("[SBP] MSG_BASE_POS_LLH (base position LLH)")

                #elif isinstance(msg, MsgBasePosEcef):
                #    print("[SBP] MSG_BASE_POS_ECEF (base position ECEF)")

                elif isinstance(msg, MsgEphemerisGPS):
                    print("[SBP] Ephemeris: GPS")

                elif isinstance(msg, MsgEphemerisGlo):
                    print("[SBP] Ephemeris: GLONASS")

                elif isinstance(msg, MsgEphemerisGal):
                    print("[SBP] Ephemeris: Galileo")

                elif isinstance(msg, MsgEphemerisBds):
                    print("[SBP] Ephemeris: BeiDou")

        except Exception:
            pass

    except socket.timeout:
        continue
