# explm.py

import socket
from sbp.client.framer import Framer

from sbp.navigation import MsgPosLLH, MsgVelNED
from sbp.imu import MsgImuRaw
from sbp.orientation import MsgOrientQuat

def main():
    TCP_IP = "195.37.48.233"
    TCP_PORT = 55555

    print("[INFO] Connecting to SBP TCP stream...")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((TCP_IP, TCP_PORT))
    print("[INFO] Connected.")

    # Framer in your libsbp needs read + write
    framer = Framer(
        sock.recv,          # read function
        lambda data: None   # dummy write function
    )

    print("[INFO] Reading SBP messages...")
    for msg, meta in framer:
        print("[SBP]", msg)

        if isinstance(msg, MsgPosLLH):
            print(" → POS LLH:", msg)
        elif isinstance(msg, MsgVelNED):
            print(" → VEL NED:", msg)
        elif isinstance(msg, MsgImuRaw):
            print(" → IMU RAW:", msg)
        elif isinstance(msg, MsgOrientQuat):
            print(" → ORIENT:", msg)


if __name__ == "__main__":
    main()
