#!/usr/bin/env python3

import json
import time
import math
from datetime import datetime
from sbp.client.drivers.network_drivers import TCPDriver
from sbp.client import Handler, Framer
from sbp.imu import MsgImuRaw
from sbp.navigation import MsgPosLLH, MsgVelNED
from colorama import Fore, Style

# port and IP of the Piksi Multi rover
ROVER_IP = "195.37.48.233"
PORT = 55555

# output JSON file
JSON_FILE = "dgps_ins_log.json"


def append_json(obj):
    """Append one JSON object per line."""
    with open(JSON_FILE, "a") as f:
        f.write(json.dumps(obj) + "\n")


def get_human_time():
    """Returns human-readable timestamp with milliseconds."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]


def main():
    print(f"{Fore.GREEN}[INFO] Connecting to Piksi Multi {ROVER_IP}:{PORT} ...{Style.RESET_ALL}")
    driver = TCPDriver(ROVER_IP, PORT)
    handler = Handler(Framer(driver.read, driver.write, verbose=False))

    print(f"{Fore.GREEN}[INFO] Connected. Streaming + Saving JSON...{Style.RESET_ALL}")
    print(f"[INFO] Output File = {JSON_FILE}")
    print("--------------------------------------------------------------")

    global count
    count = 0

    latest = {
        "lat": None, "lon": None, "alt": None,
        "vel_n": 0, "vel_e": 0, "vel_d": 0, "speed": 0,
        "acc_x": 0, "acc_y": 0, "acc_z": 0,
        "gyro_x": 0, "gyro_y": 0, "gyro_z": 0
    }

    for msg, meta in handler:

        # IMU RAW DATA
        if isinstance(msg, MsgImuRaw):
            latest["acc_x"] = msg.acc_x * 9.80665 / 1000
            latest["acc_y"] = msg.acc_y * 9.80665 / 1000
            latest["acc_z"] = msg.acc_z * 9.80665 / 1000

            latest["gyro_x"] = msg.gyr_x * math.pi / 18000
            latest["gyro_y"] = msg.gyr_y * math.pi / 18000
            latest["gyro_z"] = msg.gyr_z * math.pi / 18000

        # GNSS POSITION
        elif isinstance(msg, MsgPosLLH):
            latest["lat"] = msg.lat
            latest["lon"] = msg.lon
            latest["alt"] = msg.height

        # GNSS VELOCITY
        elif isinstance(msg, MsgVelNED):
            latest["vel_n"] = msg.n
            latest["vel_e"] = msg.e
            latest["vel_d"] = msg.d
            latest["speed"] = math.sqrt(msg.n**2 + msg.e**2 + msg.d**2)

        # SAVE ONLY WHEN GNSS FIX AVAILABLE
        if latest["lat"] is not None:
            record = {
                "timestamp": get_human_time(),
                **latest
            }

            append_json(record)
            count += 1

            print(
                f"\r{Fore.CYAN}Saved samples: {count} "
                f"| Time: {record['timestamp']} "
                f"| Speed: {latest['speed']:.2f} m/s{Style.RESET_ALL}",
                end=""
            )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{Fore.YELLOW}[INFO] Logging stopped by user")
        print(f"[INFO] Total samples saved: {count}")
        print(f"[INFO] File saved → {JSON_FILE}{Style.RESET_ALL}")
