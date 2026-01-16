import socket
import datetime

# DGPS/INS IP and Port
IP = "195.37.48.233"
PORT = 55555

# SBP message ID prefixes for your device
GNSS_PREFIXES = [
    "550201",  # GPS Time
    "550301",  # Position
    "550A02",  # Baseline
    "550E02",  # DOP
    "551002",  # Velocity
    "554A00",  # Tracking
    "551700",  # String/status messages
]

IMU_PREFIXES = [
    "550802",  # IMU Raw
    "550C02",  # IMU Aux
    "550E02",  # IMU status
    "0900",    # SBP_MSG_IMU_RAW
    "0901",    # SBP_MSG_IMU_AUX
    "0905",    # SBP_MSG_IMU_COMP
]

def now():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


print(f"[INFO] Connecting to DGPS {IP}:{PORT} ...")

try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5)
    sock.connect((IP, PORT))

    print("[INFO] Connected successfully!\n")
    print("[INFO] Reading incoming DGPS raw packets...\n")

    # open log files
    raw_f = open("raw.log", "a")
    gnss_f = open("gnss.log", "a")
    imu_f = open("imu.log", "a")

    while True:
        data = sock.recv(4096)
        if not data:
            print("[WARN] No more data received, stopping.")
            break

        hex_data = data.hex()
        raw_f.write(f"{now()} => {hex_data}\n")

        # Split into SBP messages (starts with "55")
        chunks = hex_data.split("55")
        chunks = ["55" + c for c in chunks if c != ""]

        for msg in chunks:
            prefix = msg[:6]  # first 3 bytes = message ID

            # classify message
            if prefix in GNSS_PREFIXES:
                gnss_f.write(f"{now()} => {msg}\n")

            elif prefix in IMU_PREFIXES:
                imu_f.write(f"{now()} => {msg}\n")

except socket.timeout:
    print("[ERROR] Connection timed out.")
except Exception as e:
    print("[ERROR]", e)

finally:
    print("\n[INFO] Closing connection and files.")
    try:
        sock.close()
    except:
        pass

    raw_f.close()
    gnss_f.close()
    imu_f.close()

print("[INFO] Finished logging into raw.log, gnss.log, imu.log")
