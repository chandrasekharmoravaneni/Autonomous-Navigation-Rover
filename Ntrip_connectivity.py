#!/usr/bin/env python3
import socket
import base64
import time
from datetime import datetime

# -------- EDIT THESE --------
CASTER = "www.sapos-ni-ntrip.de"
PORT   = 2101
MOUNT  = "VRS_3_4G_NI"
USER   = "ni_HochBrem10"
PASS   = "hcEX-10-747mZ"

# Optional: simulated data of rover position details !!
LAT = "5230.0000"   # DDMM.MMMM (SAPOS requires Niedersachsen region!)
LAT_DIR = "N"
LON = "01300.0000"
LON_DIR = "E"
ALT = "50.0"
# ----------------------------


# ----- GGA builder with checksum -----
def nmea_checksum(sentence):
    cs = 0
    for c in sentence:
        cs ^= ord(c)
    return f"{cs:02X}"

def build_gga():
    utc = datetime.utcnow().strftime("%H%M%S")

    core = f"GNGGA,{utc},{LAT},{LAT_DIR},{LON},{LON_DIR},1,12,1.0,{ALT},M,0.0,M,,"
    checksum = nmea_checksum(core)
    return f"${core}*{checksum}\r\n"


# Encode credentials
auth = base64.b64encode(f"{USER}:{PASS}".encode()).decode()

print(" Connecting to NTRIP caster...")

# ----- Connect -----
try:
    s = socket.create_connection((CASTER, PORT), timeout=10)
except Exception as e:
    print(" Cannot connect to caster:", e)
    exit(1)

# ----- Send GET request -----
req = (
    f"GET /{MOUNT} HTTP/1.0\r\n"
    f"Host: {CASTER}:{PORT}\r\n"
    f"User-Agent: NTRIP PythonClient\r\n"
    f"Authorization: Basic {auth}\r\n"
    f"Connection: close\r\n\r\n"
)

s.sendall(req.encode())

# ----- Read header -----
header = b""
while b"\r\n\r\n" not in header:
    chunk = s.recv(4096)
    if not chunk:
        print(" Caster closed connection during header")
        exit(1)
    header += chunk

header_text, body = header.split(b"\r\n\r\n", 1)
first_line = header_text.decode(errors="ignore").splitlines()[0]

print(" NTRIP response:", first_line)

if "200" not in first_line and "ICY 200" not in first_line:
    print("  NTRIP rejected the request")
    exit(1)

print(" NTRIP connection OK")

# ----- Send GGA -----
gga = build_gga()
s.sendall(gga.encode())
print(" Sent GGA:", gga.strip())

print(" Waiting for RTCM... (timeout = 10s)")
s.settimeout(10)

total = 0

try:
    while True:
        data = s.recv(4096)
        if not data:
            print("  Caster closed connection.")
            break

        total += len(data)
        print(f" Received {len(data)} bytes (total {total})")

        if total > 100:
            print(" SUCCESS: RTCM corrections are being received!")
            break

except socket.timeout:
    print(" RTCM timeout: No corrections received.")
except Exception as e:
    print(" Error:", e)

s.close()
print(" Connection closed.")
