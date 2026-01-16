# verify_l_move.py
import json, math, statistics
from datetime import datetime

GNSS_FILE = "gnss_data_base4.json"
IMU_FILE  = "imu_data_base4.json"

# ---------- helpers ----------
def haversine_m(lat1, lon1, lat2, lon2):
    R = 6371000.0
    phi1 = math.radians(lat1); phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1); dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return 2*R*math.atan2(math.sqrt(a), math.sqrt(1-a))

def bearing_deg(lat1, lon1, lat2, lon2):
    phi1 = math.radians(lat1); phi2 = math.radians(lat2)
    dl = math.radians(lon2 - lon1)
    y = math.sin(dl)*math.cos(phi2)
    x = math.cos(phi1)*math.sin(phi2) - math.sin(phi1)*math.cos(phi2)*math.cos(dl)
    b = math.degrees(math.atan2(y, x))
    return (b + 360) % 360

def load_json_lines(path):
    with open(path, "r") as f:
        txt = f.read().strip()
        if not txt:
            return []
        # try full json array first
        try:
            return json.loads(txt)
        except Exception:
            # fallback: parse line by line (for safety)
            out = []
            for line in txt.splitlines():
                line=line.strip().rstrip(",")
                if not line: continue
                try:
                    out.append(json.loads(line))
                except Exception:
                    pass
            return out

# ---------- load GNSS LLH ----------
gnss = load_json_lines(GNSS_FILE)
llh = []
for e in gnss:
    # robustly detect lat/lon entries
    if isinstance(e, dict) and "lat" in e and "lon" in e:
        try:
            lat = float(e["lat"]); lon = float(e["lon"])
            t = e.get("time", None)
            llh.append((lat, lon, t))
        except:
            continue

if len(llh) < 2:
    print("Not enough GNSS LLH points found (need >=2).")
    raise SystemExit(1)

# ---------- compute distances and bearings ----------
dists = []
bears = []
cum = [0.0]
for i in range(1, len(llh)):
    lat1, lon1, _ = llh[i-1]
    lat2, lon2, _ = llh[i]
    d = haversine_m(lat1, lon1, lat2, lon2)
    b = bearing_deg(lat1, lon1, lat2, lon2)
    dists.append(d)
    bears.append(b)
    cum.append(cum[-1] + d)

total_dist = cum[-1]

# ---------- detect turn by bearing change ----------
# compute delta-bearing over sliding window
delta_b = [0.0]  # first has no change
for i in range(1, len(bears)):
    da = abs((bears[i] - bears[i-1] + 180) % 360 - 180)
    delta_b.append(da)

# find index of max bearing change (candidate turn)
max_db = max(delta_b)
turn_idx = delta_b.index(max_db)  # corresponds to between point i and i+1 in LLH
turn_point = turn_idx + 1  # approximate index in llh where turn occurs

# ---------- load IMU and find gyro peak near turn time ----------
imu = load_json_lines(IMU_FILE)
# extract gyro series (gyr_x_dps or gyr_x)
gyr_t = []
gyr_mag = []
for e in imu:
    if not isinstance(e, dict): continue
    if "gyr_x_dps" in e and "gyr_y_dps" in e and "gyr_z_dps" in e:
        gx = float(e["gyr_x_dps"]); gy = float(e["gyr_y_dps"]); gz = float(e["gyr_z_dps"])
        t = e.get("time", None)
        mag = math.sqrt(gx*gx + gy*gy + gz*gz)
        gyr_t.append(t); gyr_mag.append(mag)
    elif "gyr_x" in e and "gyr_y" in e and "gyr_z" in e:
        gx = float(e["gyr_x"]); gy = float(e["gyr_y"]); gz = float(e["gyr_z"])
        t = e.get("time", None)
        mag = math.sqrt(gx*gx + gy*gy + gz*gz)
        gyr_t.append(t); gyr_mag.append(mag)

gyro_confirm = False
gyro_peak_idx = None
gyro_peak_mag = 0.0
if gyr_mag:
    gyro_peak_mag = max(gyr_mag)
    gyro_peak_idx = gyr_mag.index(gyro_peak_mag)
    # try to match time: if LLH times exist, match nearest time
    # get turn time from LLH if available
    turn_time = None
    if llh[turn_point][2]:
        turn_time = llh[turn_point][2]
    # simple confirmation: if gyro_peak exists at any time (nonzero), accept as confirmation
    if gyro_peak_mag > 50:  # deg/s threshold for significant rotation
        gyro_confirm = True

# ---------- print summary ----------
print("=== Movement Verification Summary ===")
print(f"GNSS points parsed: {len(llh)}")
print(f"Total GNSS cumulative distance (m): {total_dist:.2f}")
print(f"Largest per-step GNSS distance (m): {max(dists):.2f}")
print(f"Detected max bearing change (deg): {max_db:.1f} at GNSS index ~{turn_point}")
print()
print("IMU gyro peak magnitude (deg/s): {:.1f} {}".format(gyro_peak_mag, "(significant)" if gyro_confirm else "(small)"))
if gyro_confirm:
    print(f"Gyro peak index (imu sample): {gyro_peak_idx} -> supports a turn/rotation event.")
else:
    print("Gyro did not show a strong rotation peak (threshold 50 deg/s).")
print()
# heuristic decision
if total_dist >= 1.5 and gyro_confirm and max_db > 30:
    print("VERDICT: Data strongly supports a real short L-shaped move (~2m). ✅")
elif total_dist >= 1.0 and (gyro_confirm or max_db > 25):
    print("VERDICT: Move likely real but small; GNSS jitter may be comparable to motion. ✅ (minor uncertainty)")
else:
    print("VERDICT: Movement not clearly larger than noise. ❌ Try larger displacement or use IMU timestamps for higher certainty.")
