#!/usr/bin/env python3
"""
Master Runner — Netherlands Extract (SALES ONLY)
Runs all extraction scripts sequentially and produces a final summary.

Usage:
    python run_all.py              # Run all 26 brands
    python run_all.py mercedes     # Run single brand group
    python run_all.py audi cupra   # Run specific VW Group brands

Groups:
    stellantis  → alfa_romeo, citroen, ds, fiat, jeep, lancia, opel, peugeot
    vwgroup     → audi, cupra, seat
    renault     → alpine, dacia
    mercedes    → mercedes
    other       → honda, land_rover, lexus, mazda, mitsubishi, nissan,
                  polestar, porsche, smart, suzuki, tesla, mini
"""

import subprocess
import sys
import os
import time
from datetime import datetime

# All 26 brands mapped to their script
BRAND_MAP = {
    # Stellantis
    "alfa_romeo":  ("extract_stellantis_dealers.py", "alfa_romeo"),
    "citroen":     ("extract_stellantis_dealers.py", "citroen"),
    "ds":          ("extract_stellantis_dealers.py", "ds"),
    "fiat":        ("extract_stellantis_dealers.py", "fiat"),
    "jeep":        ("extract_stellantis_dealers.py", "jeep"),
    "lancia":      ("extract_stellantis_dealers.py", "lancia"),
    "opel":        ("extract_stellantis_dealers.py", "opel"),
    "peugeot":     ("extract_stellantis_dealers.py", "peugeot"),
    # VW Group
    "audi":        ("extract_vwgroup_dealers.py", "audi"),
    "cupra":       ("extract_vwgroup_dealers.py", "cupra"),
    "seat":        ("extract_vwgroup_dealers.py", "seat"),
    # Renault Group
    "alpine":      ("extract_renault_group_dealers.py", "alpine"),
    "dacia":       ("extract_renault_group_dealers.py", "dacia"),
    # Mercedes
    "mercedes":    ("extract_mercedes_dealers.py", None),
    # Others
    "honda":       ("extract_other_brands_dealers.py", "honda"),
    "land_rover":  ("extract_other_brands_dealers.py", "land_rover"),
    "lexus":       ("extract_other_brands_dealers.py", "lexus"),
    "mazda":       ("extract_other_brands_dealers.py", "mazda"),
    "mitsubishi":  ("extract_other_brands_dealers.py", "mitsubishi"),
    "nissan":      ("extract_other_brands_dealers.py", "nissan"),
    "polestar":    ("extract_other_brands_dealers.py", "polestar"),
    "porsche":     ("extract_other_brands_dealers.py", "porsche"),
    "smart":       ("extract_other_brands_dealers.py", "smart"),
    "suzuki":      ("extract_other_brands_dealers.py", "suzuki"),
    "tesla":       ("extract_other_brands_dealers.py", "tesla"),
    "mini":        ("extract_other_brands_dealers.py", "mini"),
}

# Convenience groups
GROUPS = {
    "stellantis": ["alfa_romeo", "citroen", "ds", "fiat", "jeep", "lancia", "opel", "peugeot"],
    "vwgroup":    ["audi", "cupra", "seat"],
    "renault":    ["alpine", "dacia"],
    "mercedes":   ["mercedes"],
    "other":      ["honda", "land_rover", "lexus", "mazda", "mitsubishi", "nissan",
                   "polestar", "porsche", "smart", "suzuki", "tesla", "mini"],
}

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def run_brand(brand_key: str) -> bool:
    script, brand_arg = BRAND_MAP[brand_key]
    script_path = os.path.join(SCRIPT_DIR, script)

    cmd = [sys.executable, script_path]
    if brand_arg:
        cmd.append(brand_arg)

    print(f"\n{'─' * 55}")
    print(f"▶  {brand_key.replace('_', ' ').title()}")
    print(f"{'─' * 55}")

    result = subprocess.run(cmd, cwd=SCRIPT_DIR)
    return result.returncode == 0


def main():
    args = sys.argv[1:]

    # Expand groups
    targets = []
    for arg in args:
        if arg in GROUPS:
            targets.extend(GROUPS[arg])
        elif arg in BRAND_MAP:
            targets.append(arg)
        else:
            print(f"Unknown brand or group: '{arg}'")
            print(f"Valid brands: {list(BRAND_MAP.keys())}")
            print(f"Valid groups: {list(GROUPS.keys())}")
            sys.exit(1)

    if not targets:
        # Default: run everything
        targets = list(BRAND_MAP.keys())

    # Deduplicate preserving order
    seen = set()
    targets = [b for b in targets if not (b in seen or seen.add(b))]

    print("=" * 55)
    print("Netherlands Extract — Master Runner (SALES ONLY)")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Brands  ({len(targets)}): {', '.join(targets)}")
    print("=" * 55)

    start = time.time()
    results = {}
    for brand in targets:
        ok = run_brand(brand)
        results[brand] = "✓" if ok else "✗ ERROR"
        time.sleep(1)  # small pause between brands

    elapsed = time.time() - start

    print("\n" + "=" * 55)
    print("FINAL SUMMARY")
    print("=" * 55)
    for brand, status in results.items():
        print(f"  {brand.replace('_', ' ').title():<20} {status}")
    print(f"\nTotal time: {elapsed / 60:.1f} minutes")
    print("=" * 55)
    print("✓ All extractions complete!")
    print(f"  Output saved to: {os.path.join(SCRIPT_DIR, '..', 'output')}")


if __name__ == "__main__":
    main()
