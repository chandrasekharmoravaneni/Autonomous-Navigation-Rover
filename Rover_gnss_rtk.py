import json
from datetime import datetime

from sbp.client.drivers.network_drivers import TCPDriver
from sbp.client.framer import Framer

from sbp.navigation import MsgPosLLH, MsgBaselineNED, MsgGPSTime, MsgDops, MsgAgeCorrections

ROVER_IP = "195.37.48.233"
PORT = 55555

# Output file
LOG_FILE = "rover_data.json"

driver = TCPDriver(ROVER_IP, PORT)
framer = Framer(driver.read, driver.write)

print("\n📡 Logging Rover GNSS data... (Ctrl+C to stop)\n")

log_entries = []

try:
    for msg, meta in framer:

        entry = {"timestamp": datetime.utcnow().isoformat()}

        # Position
        if isinstance(msg, MsgPosLLH):
            entry.update({
                "type": "pos_llh",
                "lat": msg.lat,
                "lon": msg.lon,
                "height": msg.height,
                "tow": msg.tow
            })
            print("PosLLH:", entry)

        # Baseline (RTK status)
        elif isinstance(msg, MsgBaselineNED):
            fix_type = "FLOAT"
            if msg.flags & 0x1:
                fix_type = "FIXED"

            entry.update({
                "type": "baseline_ned",
                "n": msg.n,
                "e": msg.e,
                "d": msg.d,
                "fix_type": fix_type,
                "tow": msg.tow
            })
            print("Baseline:", entry)

        # TOW (GPS Time)
        elif isinstance(msg, MsgGPSTime):
            entry.update({
                "type": "gps_time",
                "tow": msg.tow,
                "wn": msg.wn
            })
            print("GPSTime:", entry)

        # DOPS
        elif isinstance(msg, MsgDops):
            entry.update({
                "type": "dops",
                "gdop": msg.gdop,
                "pdop": msg.pdop,
                "tdop": msg.tdop,
                "hdop": msg.hdop,
                "vdop": msg.vdop
            })
            print("DOPS:", entry)

        # RTK correction age
        elif isinstance(msg, MsgAgeCorrections):
            entry.update({
                "type": "age_corrections",
                "age": msg.age
            })
            print("AgeCorrections:", entry)

        else:
            continue  # ignore other messages

        # Save entry
        log_entries.append(entry)

except KeyboardInterrupt:
    print("\n🛑 Logging stopped by user.")

# Save JSON file
with open(LOG_FILE, "w") as f:
    json.dump(log_entries, f, indent=2)

print(f"\n💾 Saved {len(log_entries)} entries to {LOG_FILE}\n")
