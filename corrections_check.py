from sbp.client.drivers.network_drivers import TCPDriver
from sbp.client import Framer
from sbp.observation import MsgObs

IP = "195.37.48.235"
PORT = 55555

driver = TCPDriver(IP, PORT)
framer = Framer(driver.read, driver.write)

print("\n--- Checking SBP Observation Messages (MsgObs) ---\n")

obs_count = 0

try:
    for msg, meta in framer:
        if isinstance(msg, MsgObs):
            obs_count += 1

            print(
                f"✔ MsgObs received | "
                f"n_obs={msg.header.n_obs}"
            )

        if obs_count >= 5:
            print("\n✅ SBP observations are being produced")
            break

except KeyboardInterrupt:
    pass
