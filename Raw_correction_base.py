from sbp.client.drivers.network_drivers import TCPDriver
from sbp.client.handler import Handler

IP = "195.37.48.235"
PORT = 55555

driver = TCPDriver(IP, PORT)
handler = Handler(driver)

print("Connecting to BASE...")

for msg, metadata in handler:
    print(hex(msg.msg_type), type(msg).__name__)
