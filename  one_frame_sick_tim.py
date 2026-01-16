#!/usr/bin/env python3
"""
Print ONE raw LiDAR frame from SICK TiM781 (CoLa-A port 2111)
Author: Satish
"""

import socket

LIDAR_IP = "192.168.0.1"
LIDAR_PORT = 2111

STX = b"\x02"
ETX = b"\x03"

def send_command(sock, cmd):
    sock.sendall(STX + cmd.encode() + ETX)

def read_one_frame(sock):
    data = b""
    while True:
        chunk = sock.recv(4096)
        if not chunk:
            break
        data += chunk
        if ETX in chunk:      # stop when ETX arrives
            break
    return data

def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((LIDAR_IP, LIDAR_PORT))
    print("Connected to LiDAR.")

    # Start scan output
    send_command(sock, "sEN LMDscandata 1")

    print("\n----- WAITING FOR ONE FRAME -----\n")

    frame = read_one_frame(sock)

    # Stop scan output
    send_command(sock, "sEN LMDscandata 0")
    sock.close()

    print("\n----- RAW FRAME START -----")
    print(frame)
    print("----- RAW FRAME END -----\n")

if __name__ == "__main__":
    main()
