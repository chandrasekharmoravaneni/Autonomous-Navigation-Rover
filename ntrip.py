import socket
import base64
import time

# ----------------------------
# SETTINGS
# ----------------------------
GNSS_IP   = "195.37.48.233"
GNSS_PORT = 55555

NTRIP_HOST = "www.sapos-ni-ntrip.de"
NTRIP_PORT = 2101
MOUNTPOINT = "VRS_3_4G_NI"
USERNAME   = "ni_HochBrem10"
PASSWORD   = "hcEX-10-747mZs"

SEND_GGA = True
GGA_INTERVAL = 5  # seconds

# ----------------------------
# CONNECT TO GNSS (TCP)
# ----------------------------
gnss_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
gnss_sock.connect((GNSS_IP, GNSS_PORT))
gnss_sock.setblocking(False)

print("✅ Connected to GNSS receiver")

# ----------------------------
# CONNECT TO NTRIP
# ----------------------------
ntrip_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
ntrip_sock.connect((NTRIP_HOST, NTRIP_PORT))

auth = base64.b64encode(f"{USERNAME}:{PASSWORD}".encode()).decode()

request = (
    f"GET /{MOUNTPOINT} HTTP/1.1\r\n"
    f"Host: {NTRIP_HOST}\r\n"
    f"Ntrip-Version: Ntrip/2.0\r\n"
    f"User-Agent: PythonNTRIP-Rover\r\n"
    f"Authorization: Basic {auth}\r\n\r\n"
)

ntrip_sock.sendall(request.encode())

response = ntrip_sock.recv(1024)
if b"200" not in response:
    raise RuntimeError("❌ NTRIP connection failed")

print("✅ Connected to NTRIP caster")

# ----------------------------
# MAIN LOOP
# ----------------------------
last_gga_time = 0
last_gga = None

print("🚀 RTCM streaming started")

while True:
    # 1️⃣ Read data from GNSS (to extract GGA if needed)
    try:
        data = gnss_sock.recv(4096)
        if data:
            text = data.decode(errors="ignore")
            for line in text.splitlines():
                if line.startswith("$GPGGA") or line.startswith("$GNGGA"):
                    last_gga = line.strip()
    except BlockingIOError:
        pass

    # 2️⃣ Send GGA upstream (VRS)
    if SEND_GGA and last_gga:
        if time.time() - last_gga_time > GGA_INTERVAL:
            ntrip_sock.sendall((last_gga + "\r\n").encode())
            last_gga_time = time.time()
            print("⬆️ Sent GGA to NTRIP")

    # 3️⃣ Receive RTCM corrections
    rtcm = ntrip_sock.recv(4096)
    if rtcm:
        gnss_sock.sendall(rtcm)

    time.sleep(0.01)
