from sbp.client.drivers.network_drivers import TCPDriver
from sbp.client import Framer

ROVER_IP = "195.37.48.233"
ROVER_PORT = 55555

driver = TCPDriver(ROVER_IP, ROVER_PORT)
framer = Framer(driver.read, driver.write)

rtcm_count = 0

print("\n--- Checking RTCM arrival at rover ---\n")

for msg, meta in framer:

    msg_id = getattr(msg, "msg_type", None)

    # RTCM passthrough messages appear in high SBP ID range
    if msg_id is not None and msg_id >= 0xF000:
        rtcm_count += 1
        print(f"✔ RTCM packet received (count={rtcm_count}, msg_id=0x{msg_id:X})")

    if rtcm_count >= 10:
        print("\n✔ CONFIRMED: Rover is RECEIVING RTCM packets")
        break
