import socket

IP = "195.37.48.233"
PORT = 55555   # or try 2101, 2111, 5000

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect((IP, PORT))

print("Connected... reading raw bytes")

while True:
    data = sock.recv(2048)
    if not data:
        break

    # RTCM always starts with 0xD3
    if b'\xd3' in data:
        print("🔥 RTCM correction frame detected!")
        print(data.hex())
    else:
        print("Not RTCM:", data[:20])
