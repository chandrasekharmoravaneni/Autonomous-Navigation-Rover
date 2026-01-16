import json
import datetime
from sbp.client.drivers.network_drivers import TCPDriver
from sbp.client import Framer
from sbp.navigation import MsgPosLLH, MsgVelNED, MsgGPSTime, MsgDops, MsgBaselineNED
from sbp.imu import MsgImuRaw


OUTPUT_FILE = "gnss_imu_log12.jsonl"   # JSON lines file (best for plotting)

def save_json(entry):
    """Append one JSON object per line."""
    with open(OUTPUT_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")


def read_sbp_stream(ip="195.37.48.233", port=55555):
    driver = TCPDriver(ip, port)
    framer = Framer(driver.read, driver.write)

    print("📡 Listening for SBP messages and saving to JSON...")

    for msg, metadata in framer:

        timestamp = datetime.datetime.utcnow().isoformat()

        # ------------------------
        # GNSS POSITION (LLH)
        # ------------------------
        if isinstance(msg, MsgPosLLH):
            data = {
                "type": "LLH",
                "time": timestamp,
                "lat": msg.lat,
                "lon": msg.lon,
                "height": msg.height
            }
            print(f"\n🌍 GNSS POSITION:", data)
            save_json(data)

        # ------------------------
        # GNSS VELOCITY
        # ------------------------
        if isinstance(msg, MsgVelNED):
            data = {
                "type": "VEL_NED",
                "time": timestamp,
                "north": msg.n,
                "east": msg.e,
                "down": msg.d
            }
            print(f"\n🚗 GNSS VELOCITY:", data)
            save_json(data)

        # ------------------------
        # GPS TIME
        # ------------------------
        if isinstance(msg, MsgGPSTime):
            data = {
                "type": "GPS_TIME",
                "time": timestamp,
                "tow": msg.tow,
                "week": msg.wn
            }
            print(f"\n⏱ GPS TIME:", data)
            save_json(data)

        # ------------------------
        # IMU RAW
        # ------------------------
        if isinstance(msg, MsgImuRaw):
            data = {
                "type": "IMU_RAW",
                "time": timestamp,
                "accel": {
                    "x": msg.acc_x / 1000.0,
                    "y": msg.acc_y / 1000.0,
                    "z": msg.acc_z / 1000.0
                },
                "gyro": {
                    "x": msg.gyr_x / 1000.0,
                    "y": msg.gyr_y / 1000.0,
                    "z": msg.gyr_z / 1000.0
                }
            }
            print(f"\n🧭 IMU RAW:", data)
            save_json(data)


if __name__ == "__main__":
    read_sbp_stream("195.37.48.235", 55555)   # ✔ use rover for IMU
