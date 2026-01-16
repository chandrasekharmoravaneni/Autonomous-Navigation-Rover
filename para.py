"""
Parse SICK TiM781 'sRA/sSN LMDscandata' telegrams from a CSV file
and extract range values in meters.

Usage:
    python3 parse_lidar_csv.py
"""

import pandas as pd
import numpy as np

# ---------- CONFIG ----------
INPUT_CSV  = "tim781_live_like_dataset.csv"
# your CSV containing telegram text
OUTPUT_CSV = "ranges_extracted.csv"       # output file
TELEGRAM_COLUMN = "telegram"              # column name in your CSV
# ----------------------------

def _twos_complement_32(h):
    """Convert 32-bit hex string to signed int."""
    v = int(h, 16)
    return v - 0x100000000 if (v & 0x80000000) else v

def parse_lmdscandata_ranges_m(telegram_text):
    """
    Parse a single CoLa-A 'sRA/sSN LMDscandata' telegram and
    return a NumPy array of range values in meters (NaN for invalid).
    """
    t = telegram_text.strip().split()
    if len(t) < 10 or t[0] not in ("sRA", "sSN") or t[1] != "LMDscandata":
        return np.array([])

    # Find the DIST1 block
    try:
        i = t.index("DIST1")
    except ValueError:
        return np.array([])

    # Extract parameters
    start_angle_1e4 = _twos_complement_32(t[i+3])  # signed start angle (1/10000°)
    step_1e4        = int(t[i+4], 16)              # step (1/10000°)
    count           = int(t[i+5], 16)              # number of range values

    # Range values (in mm)
    data = t[i+6 : i+6+count]
    if len(data) != count:
        return np.array([])

    d_mm = np.array([int(x, 16) for x in data], dtype=np.int32)
    d_m = np.where(d_mm >= 16, d_mm / 1000.0, np.nan)  # invalid <16 → NaN
    return d_m


def main():
    # Load CSV containing raw telegrams
    df = pd.read_csv(INPUT_CSV)
    if TELEGRAM_COLUMN not in df.columns:
        raise KeyError(f"Column '{TELEGRAM_COLUMN}' not found in {INPUT_CSV}")

    all_rows = []

    print(f"Processing {len(df)} telegrams...")
    for scan_id, text in enumerate(df[TELEGRAM_COLUMN].astype(str)):
        r_m = parse_lmdscandata_ranges_m(text)
        if r_m.size == 0:
            continue
        for beam_idx, rng_m in enumerate(r_m):
            if np.isnan(rng_m):
                continue
            all_rows.append((scan_id, beam_idx, float(rng_m)))

    out = pd.DataFrame(all_rows, columns=["scan_id", "beam_idx", "range_m"])
    out.to_csv(OUTPUT_CSV, index=False)
    print(f"✅ Saved {len(out)} rows to '{OUTPUT_CSV}'")


if __name__ == "__main__":
    main()
