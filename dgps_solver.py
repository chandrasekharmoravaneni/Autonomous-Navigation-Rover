# inspect_base_files.py
import json
from pathlib import Path

def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        data = f.read().strip()
        # try to parse either newline-delimited JSON or a JSON array
        try:
            return json.loads(data)
        except json.JSONDecodeError:
            # fall back to parse line-by-line
            items = []
            for line in data.splitlines():
                line = line.strip()
                if not line: 
                    continue
                try:
                    items.append(json.loads(line))
                except Exception:
                    # ignore unparsable lines
                    pass
            return items

def search_for_keys(objs, keys):
    hits = []
    for i,obj in enumerate(objs):
        text = json.dumps(obj)
        for k in keys:
            if k in text:
                hits.append((i,k))
    return hits

def main():
    eph_path = Path("eph_log1.json")
    obs_path = Path("obs2_log.json")

    eph = load_json(eph_path) if eph_path.exists() else []
    obs = load_json(obs_path) if obs_path.exists() else []

    print(f"Loaded eph entries: {len(eph)} (file: {eph_path})")
    print(f"Loaded obs entries: {len(obs)} (file: {obs_path})\n")

    # Count likely ephemeris messages (look for msg_type or typical ephem fields)
    eph_count = 0
    for entry in eph:
        if isinstance(entry, dict) and ("msg_type" in entry or "toc" in entry and "iode" in entry):
            eph_count += 1
    print("Likely ephemeris count (heuristic):", eph_count)

    # Count observations (look for 'obs' arrays or 'P'/'L_i' fields)
    obs_count = 0
    for entry in obs:
        if isinstance(entry, dict) and ("obs" in entry or ("P" in entry) or any(k in entry for k in ("n_obs","sid","L_i"))):
            obs_count += 1
    print("Likely observation entries (heuristic):", obs_count, "\n")

    # Search for base-position and age-of-corrections strings
    keys_to_find = ["BasePos", "BasePosECEF", "base_pos", "MsgBasePos", "AgeCorrections", "Age_of_corrections",
                    "age", "age_corrections", "MsgAgeCorrections", "ageCorrections"]
    print("Searching for base position / age-of-corrections keywords...")
    eph_hits = search_for_keys(eph, keys_to_find)
    obs_hits = search_for_keys(obs, keys_to_find)
    if eph_hits:
        print("Found keywords in ephemeris file (examples):", eph_hits[:10])
    else:
        print("No base-position/age keywords found in ephemeris file.")

    if obs_hits:
        print("Found keywords in obs file (examples):", obs_hits[:10])
    else:
        print("No base-position/age keywords found in obs file.")

    # Print sample timestamps / tows
    def sample_tows(list_obj, n=3):
        tows = []
        for entry in list_obj:
            if isinstance(entry, dict):
                if 'tow' in entry:
                    tows.append(entry['tow'])
                elif 'header' in entry and isinstance(entry['header'], dict) and 't' in entry['header'] and 'tow' in entry['header']['t']:
                    tows.append(entry['header']['t']['tow'])
                elif 'wn' in entry and 'tow' in entry:
                    tows.append(entry.get('tow'))
            if len(tows)>=n:
                break
        return tows

    print("\nSample TOWs from eph:", sample_tows(eph))
    print("Sample TOWs from obs:", sample_tows(obs))

if __name__ == "__main__":
    main()
