#!/usr/bin/env python3
# capture_both_obs.py
import json, time, threading
from sbp.client.drivers.network_drivers import TCPDriver
from sbp.client.framer import Framer
from sbp.observation import MsgObs
from sbp.navigation import MsgPosLLH, MsgGPSTime, MsgDops

BASE_IP = "195.37.48.235"
#ROVER_IP = "195.37.48.233"
PORT = 55555

OUT_BASE = "base_obs_log.json"
OUT_ROVER = "rover_obs_log.json"

def capture(ip, out_file, name):
    driver = TCPDriver(ip, PORT)
    framer = Framer(driver.read, driver.write)
    records = []
    print(f"[{name}] capturing from {ip}:{PORT} → {out_file}")
    try:
        for msg, meta in framer:
            entry = None
            if isinstance(msg, MsgObs):
                # lightweight capture
                entry = {"type":"Obs", "tow": msg.header.t.tow, "n_obs": msg.header.n_obs}
            elif isinstance(msg, MsgPosLLH):
                entry = {"type":"PosLLH", "tow": getattr(msg, "tow", None), "lat": msg.lat, "lon": msg.lon, "height": msg.height}
            elif isinstance(msg, MsgGPSTime):
                entry = {"type":"GPSTime", "tow": msg.tow, "wn": msg.wn}
            elif isinstance(msg, MsgDops):
                entry = {"type":"DOPS", "tow": getattr(msg, "tow", None), "hdop": msg.hdop, "pdop": msg.pdop, "gdop": msg.gdop}
            if entry:
                entry["ts"] = time.time()
                records.append(entry)
                # write incrementally
                with open(out_file, "w") as f:
                    json.dump(records, f, indent=2)
    except KeyboardInterrupt:
        print(f"[{name}] stopped, saved {len(records)} records")

t1 = threading.Thread(target=capture, args=(BASE_IP, OUT_BASE, "BASE"))
#t2 = threading.Thread(target=capture, args=(ROVER_IP, OUT_ROVER, "ROVER"))

t1.start()
#t2.start()
print("Capturing... Ctrl+C to stop.")
try:
    while t1.is_alive() and t2.is_alive():
        time.sleep(0.5)
except KeyboardInterrupt:
    print("Stopping capture threads...")
