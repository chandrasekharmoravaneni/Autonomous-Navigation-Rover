import time
from sbp.observation import MsgObs
from sbp.client.framer import Framer
from sbp.client.drivers.network_drivers import TCPDriver

# ---- CHANGE THIS TO YOUR ROVER INPUT PORT ----
ROVER_CORR_IP   = "195.37.48.235"      # rover listens on all interfaces
ROVER_CORR_PORT = 55555          # port where rover receives SBP corrections

def main():
    print("🛰️ Rover Correction Monitor")
    print(f"Listening on {ROVER_CORR_IP}:{ROVER_CORR_PORT} for SBP corrections...\n")

    # Rover receives corrections as TCP client or TCP server depending on your setup.
    driver = TCPDriver(ROVER_CORR_IP, ROVER_CORR_PORT)
    framer = Framer(driver.read, None)

    last_tow = None
    last_msg_time = time.time()

    for msg, _ in framer:

        # ----- OBSERVATION CORRECTIONS -----
        if isinstance(msg, MsgObs):
            now = time.time()
            tow = msg.header.t.tow

            print("✔ Correction received (MsgObs)")
            print(f"  Satellites in correction: {len(msg.obs)}")
            print(f"  TOW: {tow}")

            sat_list = [o.sid.sat for o in msg.obs]
            print(f"  Satellite IDs: {sat_list}")

            # Show TOW change
            if last_tow is not None:
                print(f"  ΔTOW: {tow - last_tow} seconds")

            # Show latency
            print(f"  Latency: {now - last_msg_time:.3f} sec\n")

            last_tow = tow
            last_msg_time = now

        # ----- OTHER SBP MESSAGES IF NEEDED -----
        else:
            # You can log ephemeris or others here if rover receives them
            pass

if __name__ == "__main__":
    main()
