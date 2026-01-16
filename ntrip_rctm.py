#!/usr/bin/env python3
"""
SBP + NTRIP logger with guaranteed RTCM debug prints.

- Connects to Piksi via SBP (TCPDriver -> Framer)
- Starts an NTRIP worker that sends GGA and writes incoming RTCM into the SBP driver's write function (via wrapper)
- Logs GNSS and IMU messages to JSON lines files (streamed arrays)
- Prints RTCM packet/byte counts and last-received times
- Safe shutdown on Ctrl+C
"""

import socket, base64, time, threading, signal, json
from datetime import datetime
from typing import Optional

from sbp.client.drivers.network_drivers import TCPDriver
from sbp.client import Framer

# GNSS messages
from sbp.navigation import MsgPosLLH, MsgVelNED, MsgGPSTime, MsgDops, MsgBaselineNED
# IMU
from sbp.imu import MsgImuRaw, MsgImuAux

# ---------------------------
# CONFIGURATION (edit here)
# ---------------------------
# NTRIP
CASTER = "www.sapos-ni-ntrip.de"
CASTER_PORT = 2101
MOUNT = "VRS_3_4G_NI"                # <-- no spaces
NTRIP_USER = "ni_HochBrem10"
NTRIP_PASS = "hcEX-10-747mZ"
GGA_INTERVAL = 1.0  # seconds

# Piksi / SBP TCP (your receiver)
GNSS_IP = "195.37.48.235"
GNSS_PORT = 55555

# Output files
GNSS_JSON = "gnss_data_base5.json"
IMU_JSON = "imu_data_base5.json"

# IMU scale constants (as you used)
IMU_ACC_SCALE = 9.80665 / 1000.0   # mg -> m/s^2
IMU_GYRO_SCALE = 1.0 / 16.4        # LSB -> dps

# ---------------------------
# GLOBALS
# ---------------------------
last_pos = {"lat": None, "lon": None, "h": None}
pos_lock = threading.Lock()

running = True
def stop_handler(sig, frame):
    global running
    print("\nStopping (Ctrl+C) — finishing and closing files...")
    running = False

signal.signal(signal.SIGINT, stop_handler)

# Will be set after driver creation:
real_driver_write = None   # original driver's write
# RTCM debug counters and lock
rtcm_lock = threading.Lock()
rtcm_packet_count = 0
rtcm_bytes = 0
last_rtcm_time = 0.0

# ---------------------------
# Safe JSON writer helper
# ---------------------------
class JsonStreamer:
    def __init__(self, path):
        self.path = path
        self.f = open(path, "w")
        self.first = True
        self.lock = threading.Lock()
        self.f.write("[\n")
        self.closed = False

    def write(self, obj):
        with self.lock:
            if not self.first:
                self.f.write(",\n")
            self.first = False
            json.dump(obj, self.f, default=str)
            self.f.flush()

    def close(self):
        with self.lock:
            if not self.closed:
                self.f.write("\n]")
                self.f.flush()
                self.f.close()
                self.closed = True

# ---------------------------
# Build GGA (NMEA) sentence
# ---------------------------
def build_gga(lat: float, lon: float, height: float, utc_hms: Optional[str] = None) -> Optional[str]:
    if lat is None or lon is None:
        return None
    if utc_hms is None:
        utc_hms = datetime.utcnow().strftime("%H%M%S")
    def deg_to_dm(value, is_lat):
        d = abs(value)
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
    sentence = f"GNGGA,{utc_hms},{lat_dm},{lat_dir},{lon_dm},{lon_dir},{fix},{nsat},{hdop:.1f},{height:.2f},M,0.0,M,,"
    cs = 0
    for c in sentence:
        cs ^= ord(c)
    return f"${sentence}*{cs:02X}\r\n"

# ---------------------------
# RTCM wrapper write (counts + forwards)
# ---------------------------
def driver_write_rtcm(data: bytes):
    """Wrapper used by NTRIP worker to forward RTCM to the SBP driver while counting debug stats."""
    global rtcm_packet_count, rtcm_bytes, last_rtcm_time, real_driver_write
    if not data:
        return
    with rtcm_lock:
        rtcm_packet_count += 1
        rtcm_bytes += len(data)
        last_rtcm_time = time.time()

        # print first-chunk immediate debug
        if rtcm_packet_count == 1:
            print(f"[RTCM] Packets: {rtcm_packet_count} | Bytes: {rtcm_bytes} | Last packet {time.strftime('%H:%M:%S', time.localtime())}")

        # periodic print every 20 packets
        if rtcm_packet_count % 20 == 0:
            print(f"[RTCM] Packets: {rtcm_packet_count} | Bytes: {rtcm_bytes} | Last packet {time.strftime('%H:%M:%S', time.localtime())}")

    # forward raw bytes to real driver write
    try:
        real_driver_write(data)
    except Exception as e:
        print("Error forwarding RTCM to driver.write():", e)

# ---------------------------
# Robust NTRIP worker
# ---------------------------
def ntrip_worker(driver_write_callable):
    """Connects to caster, sends GGA, receives RTCM and forwards via driver_write_callable (the wrapper)."""
    auth_b64 = base64.b64encode(f"{NTRIP_USER}:{NTRIP_PASS}".encode()).decode()
    backoff = 1

    while running:
        # wait for initial position
        with pos_lock:
            lat = last_pos["lat"]; lon = last_pos["lon"]; h = last_pos["h"]
        if lat is None:
            # no SPP yet
            time.sleep(0.1)
            continue

        try:
            s = socket.create_connection((CASTER, CASTER_PORT), timeout=10)
            s.settimeout(None)

            # Build NTRIP request (HTTP/1.1) and include initial Ntrip-GGA header (helps some casters)
            initial_gga = build_gga(lat, lon, h)
            req = (
                f"GET /{MOUNT} HTTP/1.1\r\n"
                f"Host: {CASTER}\r\n"                          # <-- don't include :port in Host for many casters
                f"User-Agent: NTRIP PythonClient\r\n"
                f"Ntrip-Version: Ntrip/2.0\r\n"
                f"Accept: */*\r\n"
                f"Connection: close\r\n"
                f"Authorization: Basic {auth_b64}\r\n"
            )
            if initial_gga:
                # send initial GGA in header for servers that expect it up-front
                req += f"Ntrip-GGA: {initial_gga.strip()}\r\n"
            req += "\r\n"
            s.sendall(req.encode())

            # read first chunk (could be headers OR immediate RTCM bytes if server uses HTTP/0.9)
            hdr = b""
            # read once to inspect
            chunk = s.recv(4096)
            if not chunk:
                raise IOError("connection closed by caster immediately")
            hdr += chunk

            header_text = None
            first_body = b""

            # If the response starts like RTCM (RTCM3 preamble 0xD3) => HTTP/0.9 (no headers), treat whole chunk as body
            if hdr[0] == 0xD3:
                # HTTP/0.9 style — no headers, everything is body
                header_text = "HTTP/0.9 (no headers) - raw RTCM"
                first_body = hdr
            else:
                # try to accumulate until we find header terminator
                if b"\r\n\r\n" not in hdr:
                    # attempt to read a bit more, but don't block forever
                    s.settimeout(0.5)
                    try:
                        while b"\r\n\r\n" not in hdr:
                            more = s.recv(4096)
                            if not more:
                                break
                            hdr += more
                            if len(hdr) > 65536:
                                break
                    except socket.timeout:
                        pass
                    finally:
                        s.settimeout(None)

                if b"\r\n\r\n" in hdr:
                    header_part, first_body = hdr.split(b"\r\n\r\n", 1)
                    header_text = header_part.decode(errors="ignore")
                else:
                    # no header terminator found; treat as HTTP/0.9-like body fallback
                    # if header-looking text present, show it; else mark as unknown
                    try:
                        header_text = hdr.decode(errors="ignore")[:200]
                    except Exception:
                        header_text = "Unknown response (no CRLFCRLF)"
                    first_body = b""

            print("NTRIP header:", header_text.splitlines()[0].strip() if header_text else "None")

            # if header_text contains an HTTP error -> reject
            if header_text and ("401" in header_text or "401 Unauthorized" in header_text):
                print("NTRIP rejected (401). Check credentials.")
                s.close()
                time.sleep(backoff)
                backoff = min(60, backoff * 2)
                continue

            # treat ICY/200 or HTTP 200 as success; for HTTP/0.9 we also accept as success
            ok = False
            if header_text:
                if ("200" in header_text) or header_text.startswith("ICY") or header_text.startswith("HTTP/0.9") or header_text.startswith("HTTP/1.0") or header_text.startswith("HTTP/1.1"):
                    ok = True
            else:
                ok = True

            if not ok:
                print("NTRIP rejected:", header_text)
                s.close()
                time.sleep(backoff)
                backoff = min(60, backoff * 2)
                continue

            # forward initial bytes if present
            if first_body:
                driver_write_callable(first_body)

            # start GGA sender thread for this socket
            def gga_sender(sock):
                last_sent = 0.0
                while running:
                    if time.time() - last_sent >= GGA_INTERVAL:
                        with pos_lock:
                            la = last_pos["lat"]; lo = last_pos["lon"]; hh = last_pos["h"]
                        gga = build_gga(la, lo, hh)
                        if gga:
                            try:
                                sock.sendall(gga.encode())
                            except Exception:
                                return
                        last_sent = time.time()
                    time.sleep(0.05)

            threading.Thread(target=gga_sender, args=(s,), daemon=True).start()

            # RTCM receive loop (forward & debug)
            backoff = 1
            while running:
                data = s.recv(4096)
                if not data:
                    print("NTRIP caster closed connection.")
                    break

                # forward RTCM via provided callable (which should be driver_write_rtcm)
                driver_write_callable(data)

                # if no rtcms in 10s -> warn (uses last_rtcm_time)
                with rtcm_lock:
                    if time.time() - last_rtcm_time > 10:
                        print("⚠️ WARNING: No RTCM corrections received for 10 seconds")
                        # reset timer so message isn't spammed
                        last_rtcm_time = time.time()

            try:
                s.close()
            except:
                pass

        except Exception as exc:
            print("NTRIP connection error:", exc)
            time.sleep(backoff)
            backoff = min(60, backoff * 2)

# ---------------------------
# Main: SBP connect, start NTRIP, log messages
# ---------------------------
def main():
    global running, real_driver_write
    # prepare JSON streamers
    gnss_stream = JsonStreamer(GNSS_JSON)
    imu_stream = JsonStreamer(IMU_JSON)

    # connect to receiver
    print(f"Connecting to SBP receiver {GNSS_IP}:{GNSS_PORT} ...")
    driver = TCPDriver(GNSS_IP, GNSS_PORT, timeout=5, reconnect=True)

    # SAVE the real driver.write BEFORE creating Framer or wrapping it
    real_driver_write = driver.write

    # Use the real_driver_write for Framer so SBP writing remains the same.
    framer = Framer(driver.read, real_driver_write)
    print("Connected. Starting NTRIP worker...")

    # start NTRIP thread with wrapper
    ntrip_thread = threading.Thread(target=ntrip_worker, args=(driver_write_rtcm,), daemon=True)
    ntrip_thread.start()

    try:
        for msg, meta in framer:
            if not running:
                break
            timestamp = datetime.utcnow().isoformat()

            if isinstance(msg, MsgPosLLH):
                # RTK status: flags lower 3 bits (SBP user mapping)
                status = msg.flags & 0x7 if hasattr(msg, "flags") else None
                status_text = None
                if status is not None:
                    if status == 7: status_text = "RTK FIX"
                    elif status == 6: status_text = "RTK FLOAT"
                    elif status == 5: status_text = "DGNSS"
                    elif status == 4: status_text = "GNSS FIX"
                    elif status == 1: status_text = "SINGLE"
                    else: status_text = f"Other({status})"

                # update last_pos for GGA
                with pos_lock:
                    last_pos["lat"] = msg.lat
                    last_pos["lon"] = msg.lon
                    last_pos["h"] = msg.height

                obj = {
                    "type": "LLH", "time": timestamp, "tow": msg.tow,
                    "lat": msg.lat, "lon": msg.lon, "height": msg.height,
                    "rtk_status": status_text
                }
                gnss_stream.write(obj)
                print("LLH:", obj)
                continue

            if isinstance(msg, MsgVelNED):
                obj = {
                    "type": "VEL", "time": timestamp, "tow": msg.tow,
                    "vel_n_mps": msg.n / 1000.0,
                    "vel_e_mps": msg.e / 1000.0,
                    "vel_d_mps": msg.d / 1000.0,
                }
                obj["speed_mps"] = (obj["vel_n_mps"]**2 + obj["vel_e_mps"]**2 + obj["vel_d_mps"]**2)**0.5
                obj["speed_horiz_mps"] = (obj["vel_n_mps"]**2 + obj["vel_e_mps"]**2)**0.5
                gnss_stream.write(obj)
                print("VEL:", obj)
                continue

            if isinstance(msg, MsgGPSTime):
                obj = {"type": "TIME", "time": timestamp, "tow": msg.tow, "week": msg.wn}
                gnss_stream.write(obj)
                print("GPS TIME:", obj)
                continue

            if isinstance(msg, MsgDops):
                obj = {"type": "DOPS", "time": timestamp, "tow": msg.tow,
                       "hdop": msg.hdop / 10.0, "vdop": msg.vdop / 10.0, "pdop": msg.pdop / 10.0}
                gnss_stream.write(obj)
                print("DOPS:", obj)
                continue

            if isinstance(msg, MsgBaselineNED):
                obj = {"type": "BASELINE", "time": timestamp, "tow": msg.tow,
                       "baseline_n_m": msg.n / 1000.0, "baseline_e_m": msg.e / 1000.0, "baseline_d_m": msg.d / 1000.0}
                gnss_stream.write(obj)
                print("BASELINE:", obj)
                continue

            if isinstance(msg, MsgImuRaw):
                acc_x = msg.acc_x * IMU_ACC_SCALE
                acc_y = msg.acc_y * IMU_ACC_SCALE
                acc_z = msg.acc_z * IMU_ACC_SCALE
                gyr_x = msg.gyr_x * IMU_GYRO_SCALE
                gyr_y = msg.gyr_y * IMU_GYRO_SCALE
                gyr_z = msg.gyr_z * IMU_GYRO_SCALE
                obj = {"type": "IMU_RAW", "time": timestamp, "tow": msg.tow,
                       "acc_x_mps2": acc_x, "acc_y_mps2": acc_y, "acc_z_mps2": acc_z,
                       "gyr_x_dps": gyr_x, "gyr_y_dps": gyr_y, "gyr_z_dps": gyr_z}
                imu_stream.write(obj)
                print("IMU RAW (converted):", obj)
                continue

            if isinstance(msg, MsgImuAux):
                obj = {"type": "IMU_AUX", "time": timestamp, "temp_raw": msg.temp, "imu_type": msg.imu_type}
                imu_stream.write(obj)
                print("IMU AUX:", obj)
                continue

    except Exception as e:
        print("Main loop error:", e)

    finally:
        # Close streamers cleanly
        try:
            gnss_stream.close()
            imu_stream.close()
        except Exception:
            pass
        print("Files closed. Exiting.")

if __name__ == "__main__":
    main()
