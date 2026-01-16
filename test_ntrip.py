import socket
s = socket.socket()
s.settimeout(5)
s.connect(("www.sapos-ni-ntrip.de", 2101))
s.send(b"GET /VRS_3_4G_NI HTTP/1.1\r\nHost: www.sapos-ni-ntrip.de\r\nUser-Agent:pytest\r\n\r\n")
resp = s.recv(4096)
s.close()
print(resp[:800].hex())
