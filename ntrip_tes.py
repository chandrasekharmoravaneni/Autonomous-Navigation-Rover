# save as sbp_ntrip_logger_debug.py (based on your current script)
#!/usr/bin/env python3
"""
SBP + NTRIP logger (debuggable): same as before but prints clear NTRIP status,
GGA sends, and RTCM bytes forwarded so you can see 'NTRIP has Internet' in the console.
"""

import os
import socket
import base64
import time
import threading
import signal
import json
import logging
import errno
from datetime import datetime, timezone
from typing import Optional, Callable

from sbp.client.drivers.network_drivers import TCPDriver
from sbp.client import Framer

# GNSS messages
from sbp.navigation import MsgPosLLH, MsgVelNED, MsgGPSTime, MsgDops, MsgBaselineNED
# IMU
from sbp.imu import MsgImuRaw, MsgImuAux

# ---------------------------
# CONFIGURATION (env or defaults)
# ---------------------------
CASTER = os.getenv("CASTER", "www.sapos-ni-ntrip.de")
CASTER_PORT = int(os.getenv("CASTER_PORT", "2101"))
MOUNT = os.getenv("MOUNT", "VRS_3_4G_NI")

NTRIP_USER = os.getenv("NTRIP_USER")
NTRIP_PASS = os.getenv("NTRIP_PASS")

GGA_INTERVAL = float(os.getenv("GGA_INTERVAL", "1.0"))

GNSS_IP = os.getenv("GNSS_IP", "195.37.48.233")
GNSS_PORT = int(os.getenv("GNSS_PORT", "55555"))

GNSS_JSON = os.getenv("GNSS_JSON", "gnss_data_base2.json")
IMU_JSON = os.getenv("IMU_JSON", "imu_data_base2.json")

IMU_ACC_SCALE = float(os.getenv("IMU_ACC_SCALE", str(9.80665 / 1000.0)))
IMU_GYRO_SCALE = float(os.getenv("IMU_GYRO_SCALE", str(1.0 / 16.4)))

SHOW_STATUS_ONLY = os.getenv("SHOW_STATUS_ONLY", "0") in ("1", "true", "True", "YES", "yes", "y")

# ---------------------------
# GLOBALS
# ---------------------------
last_pos = {"lat": None, "lon": None, "h": None}
pos_lock = threading.Lock()

# NTRIP status dict (for UI/debug)
ntrip_status = {
    "connected": False,
    "last_header": None,
    "last_rx_time": None,
    "bytes_forwarded_total": 0
}
ntrip_lock = threading.Lock()

# current readable RTK status for UI
current_status = {"rtk_text": "UNKNOWN", "time": None}
status_lock = threading.Lock()

running = True


def stop_handler(sig, frame):
    global running
    logging.info("Signal received, stopping...")
    running = False


signal.signal(signal.SIGINT, stop_handler)
signal.signal(signal.SIGTERM, stop_handler)

# ---------------------------
# Safe JSON writer helper (fsync on write)
# ---------------------------
class JsonStreamer:
    def __init__(self, path: str):
        self.path = path
        self.f = open(path, "w", encoding="utf-8")
        self.first = True
        self.lock = threading.Lock()
        self.f.write("[\n")
        self.closed = False

    def write(self, obj):
        with self.lock:
            if not self.first:
                self.f.write(",\n")
            self.first = False
            json.dump(obj, self.f, default=str, ensure_ascii=False)
            self.f.write("\n")
            self.f.flush()
            try:
                os.fsync(self.f.fileno())
            except OSError:
                pass

    def close(self):
        with self.lock:
            if not self.closed:
                self.f.write("]\n")
                self.f.flush()
                try:
                    os.fsync(self.f.fileno())
                except OSError:
                    pass
                self.f.close()
                self.closed = True


# ---------------------------
# Build GGA (NMEA) sentence
# ---------------------------
def build_gga(lat: Optional[float], lon: Optional[float], height: Optional[float], utc_time: Optional[datetime] = None) -> Optional[str]:
    if lat is None or lon is None:
        return None
    if utc_time is None:
        utc_time = datetime.utcnow().replace(tzinfo=timezone.utc)
    utc_hms = utc_time.strftime("%H%M%S")

    def deg_to_dm(value: float, is_lat: bool) -> str:
        d = abs(float(value))
        deg = int(d)
        minutes = (d - deg) * 60.0
        if is_lat:
            return f"{deg:02d}{minutes:07.4f}"
        return f"{deg:03d}{minutes:07.4f}"

    lat_dm = deg_to_dm(lat, True)
    lon_dm = deg_to_dm(lon, False)
    lat_dir = "N" if lat >= 0 else "S"
    lon_dir = "E" if lon >= 0 else "W"
    fix = 1
    nsat = 8
    hdop = 1.0
    height_val = float(height) if height is not None else 0.0
    sentence = f"GNGGA,{utc_hms},{lat_dm},{lat_dir},{lon_dm},{lon_dir},{fix},{nsat},{hdop:.1f},{height_val:.2f},M,0.0,M,,"
    cs = 0
    for c in sentence:
        cs ^= ord(c)
    return f"${sentence}*{cs:02X}\r\n"


# ---------------------------
# RTK status helpers & UI thread
# ---------------------------
def rtk_status_from_flags(flags: Optional[int]) -> str:
    if flags is None:
        return "UNKNOWN"
    v = flags & 0x7
    if v == 7:
        return "RTK FIX"
    if v == 6:
        return "RTK FLOAT"
    if v == 5:
        return "DGNSS"
    if v == 4:
        return "GNSS FIX"
    if v == 1:
        return "SINGLE"
    return f"OTHER({v})"


def status_printer_thread():
    while running:
        with status_lock:
            txt = current_status["rtk_text"]
            ts = current_status["time"]
        with ntrip_lock:
            connected = ntrip_status["connected"]
            last_header = ntrip_status["last_header"]
            bytes_total = ntrip_status["bytes_forwarded_total"]
        ts_str = ts if ts is not None else "--"
        conn_str = "NTRIP:OK" if connected else "NTRIP:DOWN"
        line = f"[{ts_str}] {conn_str} | RTK: {txt} | RTCM bytes: {bytes_total}"
        # concise status (no ANSI to keep logs clean)
        print("\r" + line.ljust(120), end="", flush=True)
        time.sleep(1)
    print("\r" + " " * 120 + "\r", end="", flush=True)


# ---------------------------
# Robust NTRIP worker (with visible logging)
# ---------------------------
def ntrip_worker(driver_write: Callable[[bytes], None]):
    if not (NTRIP_USER and NTRIP_PASS):
        logging.error("NTRIP credentials not provided; skipping NTRIP worker.")
        return

    auth_b64 = base64.b64encode(f"{NTRIP_USER}:{NTRIP_PASS}".encode("utf-8")).decode("ascii")
    backoff = 1
    while running:
        with pos_lock:
            lat = last_pos["lat"]
            lon = last_pos["lon"]
            h = last_pos["h"]
        if lat is None:
            time.sleep(0.1)
            continue

        try:
            logging.info("NTRIP: connecting to %s:%d mount %s", CASTER, CASTER_PORT, MOUNT)
            s = socket.create_connection((CASTER, CASTER_PORT), timeout=10)
            s.settimeout(None)

            req = (
                f"GET /{MOUNT} HTTP/1.0\r\n"
                f"Host: {CASTER}:{CASTER_PORT}\r\n"
                f"User-Agent: NTRIP-PythonClient/1.0\r\n"
                f"Accept: */*\r\n"
                f"Connection: close\r\n"
                f"Authorization: Basic {auth_b64}\r\n"
                "\r\n"
            )
            s.sendall(req.encode("ascii"))

            # read header
            hdr = b""
            while b"\r\n\r\n" not in hdr:
                chunk = s.recv(4096)
                if not chunk:
                    raise IOError("connection closed while reading header")
                hdr += chunk
                if len(hdr) > 65536:
                    raise IOError("HTTP header too large")
            header, first_body = hdr.split(b"\r\n\r\n", 1)
            header_text = header.decode(errors="ignore")
            first_line = header_text.splitlines()[0].strip() if header_text else "<no header>"
            logging.info("NTRIP header: %s", first_line)
            with ntrip_lock:
                ntrip_status["connected"] = True
                ntrip_status["last_header"] = first_line

            if ("200" not in header_text) and ("ICY 200" not in header_text):
                logging.error("NTRIP rejected: %s", first_line)
                s.close()
                with ntrip_lock:
                    ntrip_status["connected"] = False
                time.sleep(backoff)
                backoff = min(60, backoff * 2)
                continue

            # forward any initial body bytes
            if first_body:
                driver_write(first_body)
                with ntrip_lock:
                    ntrip_status["bytes_forwarded_total"] += len(first_body)
                    ntrip_status["last_rx_time"] = datetime.utcnow().isoformat()
                logging.info("NTRIP: forwarded initial body bytes %d", len(first_body))

            # GGA sender
            def gga_sender(sock: socket.socket):
                last_sent = 0.0
                try:
                    while running:
                        now = time.time()
                        if now - last_sent >= GGA_INTERVAL:
                            with pos_lock:
                                la = last_pos["lat"]
                                lo = last_pos["lon"]
                                hh = last_pos["h"]
                            gga = build_gga(la, lo, hh)
                            if gga:
                                try:
                                    sock.sendall(gga.encode("ascii"))
                                    logging.info("NTRIP: sent GGA: %s", gga.strip())
                                except Exception as e:
                                    logging.warning("GGA send error: %s", e)
                                    return
                            last_sent = now
                        time.sleep(0.05)
                except Exception:
                    logging.exception("GGA sender crashed")

            gga_thread = threading.Thread(target=gga_sender, args=(s,), daemon=True)
            gga_thread.start()

            # receive loop
            backoff = 1
            while running:
                try:
                    data = s.recv(4096)
                    if not data:
                        logging.info("NTRIP caster closed connection.")
                        break
                    # forward raw RTCM bytes into SBP driver's write (binary passthrough)
                    try:
                        driver_write(data)
                        with ntrip_lock:
                            ntrip_status["bytes_forwarded_total"] += len(data)
                            ntrip_status["last_rx_time"] = datetime.utcnow().isoformat()
                        logging.debug("NTRIP: forwarded %d RTCM bytes (total %d)", len(data), ntrip_status["bytes_forwarded_total"])
                    except Exception as ex:
                        logging.exception("Failed writing RTCM to driver: %s", ex)
                        break
                except socket.timeout:
                    continue
                except (OSError, IOError) as ioe:
                    logging.exception("Receive error from NTRIP caster: %s", ioe)
                    break

            try:
                s.close()
            except Exception:
                pass

        except Exception as exc:
            logging.exception("NTRIP connection error: %s", exc)
            with ntrip_lock:
                ntrip_status["connected"] = False
            time.sleep(backoff)
            backoff = min(60, backoff * 2)
    # ensure flag off on exit
    with ntrip_lock:
        ntrip_status["connected"] = False


# ---------------------------
# Main: SBP connect, start NTRIP, log messages
# ---------------------------
def main():
    global running
    level = logging.DEBUG if not SHOW_STATUS_ONLY else logging.WARNING
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(message)s")

    gnss_stream = JsonStreamer(GNSS_JSON)
    imu_stream = JsonStreamer(IMU_JSON)

    logging.info("Connecting to SBP receiver %s:%d ...", GNSS_IP, GNSS_PORT)
    driver = TCPDriver(GNSS_IP, GNSS_PORT, timeout=5, reconnect=True)
    framer = Framer(driver.read, driver.write)

    logging.info("Starting NTRIP worker...")
    ntrip_thread = threading.Thread(target=ntrip_worker, args=(driver.write,), daemon=True)
    ntrip_thread.start()

    printer_thread = threading.Thread(target=status_printer_thread, daemon=True)
    printer_thread.start()

    try:
        for msg, meta in framer:
            if not running:
                break
            timestamp = datetime.utcnow().replace(tzinfo=timezone.utc).isoformat()

            try:
                if isinstance(msg, MsgPosLLH):
                    flags = getattr(msg, "flags", None)
                    status_text = rtk_status_from_flags(flags)

                    with pos_lock:
                        last_pos["lat"] = msg.lat
                        last_pos["lon"] = msg.lon
                        last_pos["h"] = msg.height

                    with status_lock:
                        current_status["rtk_text"] = status_text
                        current_status["time"] = timestamp

                    obj = {
                        "type": "LLH",
                        "time": timestamp,
                        "tow": getattr(msg, "tow", None),
                        "lat": msg.lat,
                        "lon": msg.lon,
                        "height": msg.height,
                        "rtk_status": status_text,
                    }
                    gnss_stream.write(obj)
                    if not SHOW_STATUS_ONLY:
                        logging.info("LLH: %s", obj)
                    continue

                # ... rest of message handling identical to your earlier script ...
                if isinstance(msg, MsgVelNED):
                    obj = {
                        "type": "VEL",
                        "time": timestamp,
                        "tow": getattr(msg, "tow", None),
                        "vel_n_mps": msg.n / 1000.0,
                        "vel_e_mps": msg.e / 1000.0,
                        "vel_d_mps": msg.d / 1000.0,
                    }
                    obj["speed_mps"] = (obj["vel_n_mps"] ** 2 + obj["vel_e_mps"] ** 2 + obj["vel_d_mps"] ** 2) ** 0.5
                    obj["speed_horiz_mps"] = (obj["vel_n_mps"] ** 2 + obj["vel_e_mps"] ** 2) ** 0.5
                    gnss_stream.write(obj)
                    if not SHOW_STATUS_ONLY:
                        logging.info("VEL: %s", obj)
                    continue

                if isinstance(msg, MsgGPSTime):
                    obj = {"type": "TIME", "time": timestamp, "tow": getattr(msg, "tow", None), "week": getattr(msg, "wn", None)}
                    gnss_stream.write(obj)
                    if not SHOW_STATUS_ONLY:
                        logging.info("GPS TIME: %s", obj)
                    continue

                if isinstance(msg, MsgDops):
                    obj = {
                        "type": "DOPS",
                        "time": timestamp,
                        "tow": getattr(msg, "tow", None),
                        "hdop": getattr(msg, "hdop", 0) / 10.0,
                        "vdop": getattr(msg, "vdop", 0) / 10.0,
                        "pdop": getattr(msg, "pdop", 0) / 10.0,
                    }
                    gnss_stream.write(obj)
                    if not SHOW_STATUS_ONLY:
                        logging.info("DOPS: %s", obj)
                    continue

                if isinstance(msg, MsgBaselineNED):
                    obj = {
                        "type": "BASELINE",
                        "time": timestamp,
                        "tow": getattr(msg, "tow", None),
                        "baseline_n_m": msg.n / 1000.0,
                        "baseline_e_m": msg.e / 1000.0,
                        "baseline_d_m": msg.d / 1000.0,
                    }
                    gnss_stream.write(obj)
                    if not SHOW_STATUS_ONLY:
                        logging.info("BASELINE: %s", obj)
                    continue

                if isinstance(msg, MsgImuRaw):
                    acc_x = msg.acc_x * IMU_ACC_SCALE
                    acc_y = msg.acc_y * IMU_ACC_SCALE
                    acc_z = msg.acc_z * IMU_ACC_SCALE
                    gyr_x = msg.gyr_x * IMU_GYRO_SCALE
                    gyr_y = msg.gyr_y * IMU_GYRO_SCALE
                    gyr_z = msg.gyr_z * IMU_GYRO_SCALE
                    obj = {
                        "type": "IMU_RAW",
                        "time": timestamp,
                        "tow": getattr(msg, "tow", None),
                        "acc_x_mps2": acc_x,
                        "acc_y_mps2": acc_y,
                        "acc_z_mps2": acc_z,
                        "gyr_x_dps": gyr_x,
                        "gyr_y_dps": gyr_y,
                        "gyr_z_dps": gyr_z,
                    }
                    imu_stream.write(obj)
                    if not SHOW_STATUS_ONLY:
                        logging.debug("IMU RAW: %s", obj)
                    continue

                if isinstance(msg, MsgImuAux):
                    obj = {"type": "IMU_AUX", "time": timestamp, "temp_raw": getattr(msg, "temp", None), "imu_type": getattr(msg, "imu_type", None)}
                    imu_stream.write(obj)
                    if not SHOW_STATUS_ONLY:
                        logging.debug("IMU AUX: %s", obj)
                    continue

            except Exception:
                logging.exception("Error processing message")

    except Exception:
        logging.exception("Main loop error")
    finally:
        logging.info("Closing streams and exiting.")
        try:
            gnss_stream.close()
            imu_stream.close()
        except Exception:
            logging.exception("Error closing streams")


if __name__ == "__main__":
    main()
