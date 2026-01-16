import base64
import socket
import threading
import time

from sbp.client.drivers.network_drivers import TCPDriver
from sbp.client import Framer

from sbp.navigation import MsgPosLLH, MsgPosECEF, MsgVelNED
from sbp.imu import MsgImuRaw
from sbp.system import MsgHeartbeat


# ------------------------------------------------------
# SBP GNSS STREAM (Swift Navigation)
# ------------------------------------------------------
IP = "195.37.48.235"
PORT = 55555

driver = TCPDriver(IP, PORT)
framer = Framer(driver.read, driver.write)

# ------------------------------------------------------
# SAPOS NTRIP CONFIG
# ------------------------------------------------------
NTRIP_HOST = "www.sapos-ni-ntrip.de"
NTRIP_PORT = 2101
MOUNTPOINT = "VRS_3_4G_NI"

NTRIP_USERNAME = "ni_HochBrem10"
NTRIP_PASSWORD = "hcEX-10-747mZ"

# Store latest LLH position for GGA
latest_lat = None
latest_lon = None
latest_h = None


# ------------------------------------------------------
# Generate NMEA GGA Sentence for VRS SAPOS
# ------------------------------------------------------
def generate_gga(lat, lon, height):
    if lat is None or lon is None:
        return None

    # Convert to NMEA format
    lat_deg = int(abs(lat))
    lat_min = (abs(lat) - lat_deg) * 60
    lat_dir = "N" if lat >= 0 else "S"

    lon_deg = int(abs(lon))
    lon_min = (abs(lon) - lon_deg) * 60
    lon_dir = "E" if lon >= 0 else "W"

    # Time (dummy time)
    t = time.strftime("%H%M%S", time.gmtime())

    gga = f"GPGGA,{t},{lat_deg:02d}{lat_min:09.6f},{lat_dir},{lon_deg:03d}{lon_min:09.6f},{lon_dir},1,12,1.0,{height:.1f},M,0.0,M,,"

    # Checksum
    checksum = 0
    for c in gga:
        checksum ^= ord(c)

    return f"${gga}*{checksum:02X}\r\n"


# ------------------------------------------------------
# NTRIP Client (SAPOS + GGA)
# ------------------------------------------------------
def ntrip_client():
    global latest_lat, latest_lon, latest_h

    print("Connecting to NTRIP caster...")

    # TCP connection
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((NTRIP_HOST, NTRIP_PORT))

    # Encode username:password
    auth_str = f"{NTRIP_USERNAME}:{NTRIP_PASSWORD}"
    auth_b64 = base64.b64encode(auth_str.encode()).decode()

    # Send NTRIP GET request
    headers = (
        f"GET /{MOUNTPOINT} HTTP/1.1\r\n"
        f"Host: {NTRIP_HOST}\r\n"
        f"Ntrip-Version: Ntrip/2.0\r\n"
        f"User-Agent: Python-NTRIP\r\n"
        f"Authorization: Basic {auth_b64}\r\n"
        f"Connection: close\r\n\r\n"
    )
    s.send(headers.encode())
    print("NTRIP request sent. Waiting for RTCM...")

    # Thread to send GGA every 5 seconds
    def send_gga():
        while True:
            if latest_lat is not None:
                gga = generate_gga(latest_lat, latest_lon, latest_h)
                if gga:
                    print("Sending GGA:", gga.strip())
                    try:
                        s.send(gga.encode())
                    except Exception:
                        pass
            time.sleep(5)

    threading.Thread(target=send_gga, daemon=True).start()

    # Receive RTCM data
    while True:
        data = s.recv(4096)
        if not data:
            print("NTRIP stopped.")
            break

        driver.write(data)

    s.close()


threading.Thread(target=ntrip_client, daemon=True).start()


# ------------------------------------------------------
# MAIN SBP LOOP (with RTK FIX/FLOAT)
# ------------------------------------------------------
print("Listening to SBP stream...")

for msg, meta in framer:

    if isinstance(msg, MsgPosLLH):

        latest_lat = msg.lat
        latest_lon = msg.lon
        latest_h = msg.height

        # Extract RTK fix type
        status = msg.flags & 0x7

        if status == 7:
            fix_text = "RTK FIXED"
        elif status == 6:
            fix_text = "RTK FLOAT"
        elif status == 5:
            fix_text = "DGNSS"
        elif status == 4:
            fix_text = "GNSS FIX"
        else:
            fix_text = f"Other Fix ({status})"

        print(
            f"GNSS LLH → lat={msg.lat}, lon={msg.lon}, h={msg.height} "
            f"| Status: {fix_text}"
        )

    elif isinstance(msg, MsgPosECEF):
        print(f"GNSS ECEF → x={msg.x}, y={msg.y}, z={msg.z}")

    elif isinstance(msg, MsgVelNED):
        print(f"Vel NED → {msg.n:.2f}, {msg.e:.2f}, {msg.d:.2f} m/s")

    elif isinstance(msg, MsgImuRaw):
        print(
            f"IMU Raw → acc=({msg.acc_x}, {msg.acc_y}, {msg.acc_z}), "
            f"gyro=({msg.gyr_x}, {msg.gyr_y}, {msg.gyr_z})"
        )

    elif isinstance(msg, MsgHeartbeat):
        print("Heartbeat OK")
