#!/usr/bin/env python3
"""
Renault Group Dealer Extractor — Netherlands (SALES ONLY)
Brands: Alpine, Dacia
Uses the Renault Group Dealer Locator API (api-dl.renault.com).
"""

import json
import csv
import os
from datetime import datetime
import requests
import time

API_BASE = "https://api-dl.renault.com/api/v1/dealers"

BRANDS = {
    "alpine": {
        "name": "Alpine",
        "brand_code": "alpine",
        "country": "NL",
        "language": "nl",
    },
    "dacia": {
        "name": "Dacia",
        "brand_code": "dacia",
        "country": "NL",
        "language": "nl",
    },
}

HEADERS = {
    "accept": "application/json",
    "accept-language": "nl-NL,nl;q=0.9",
    "origin": "https://www.dacia.nl",
    "referer": "https://www.dacia.nl/",
    "user-agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
}

# Dutch city coordinates for geo-based search
NL_COORDS = [
    ("Amsterdam", 52.3676, 4.9041),
    ("Rotterdam", 51.9244, 4.4777),
    ("Den Haag", 52.0705, 4.3007),
    ("Utrecht", 52.0907, 5.1214),
    ("Eindhoven", 51.4416, 5.4697),
    ("Groningen", 53.2194, 6.5665),
    ("Tilburg", 51.5555, 5.0913),
    ("Almere", 52.3508, 5.2647),
    ("Breda", 51.5719, 4.7683),
    ("Nijmegen", 51.8426, 5.8546),
    ("Maastricht", 50.8514, 5.6910),
    ("Zwolle", 52.5168, 6.0830),
    ("Enschede", 52.2215, 6.8937),
    ("Leeuwarden", 53.2012, 5.7999),
    ("Middelburg", 51.4987, 3.6136),
]


def extract_brand_dealers(brand_key: str) -> list:
    config = BRANDS[brand_key]
    brand_name = config["name"]

    print(f"\n{'=' * 55}")
    print(f"Extracting {brand_name} dealers (Netherlands, SALES ONLY)...")
    print(f"{'=' * 55}")

    all_dealers_raw = []
    seen_ids = set()

    for city_name, lat, lng in NL_COORDS:
        print(f"  Searching near {city_name}...")
        params = {
            "brand": config["brand_code"],
            "country": config["country"],
            "language": config["language"],
            "lat": str(lat),
            "lng": str(lng),
            "radius": "150",
            "limit": "100",
            "activity": "VENTE",  # French for SALES (Renault Group uses FR terms)
        }

        # Update referer per brand
        HEADERS["origin"] = f"https://www.{brand_key}.nl"
        HEADERS["referer"] = f"https://www.{brand_key}.nl/"

        try:
            resp = requests.get(API_BASE, headers=HEADERS, params=params, timeout=30)

            if resp.status_code == 404:
                print(f"    No results for {city_name}")
                time.sleep(1)
                continue
            elif resp.status_code != 200:
                print(f"    HTTP {resp.status_code} — skipping {city_name}")
                time.sleep(2)
                continue

            data = resp.json()
            # Renault API returns list directly or under 'dealers' key
            if isinstance(data, list):
                dealers_list = data
            else:
                dealers_list = data.get("dealers", data.get("results", []))

            new_count = 0
            for dealer in dealers_list:
                did = dealer.get("dealerId", dealer.get("id", ""))
                if did and did not in seen_ids:
                    seen_ids.add(did)
                    all_dealers_raw.append(dealer)
                    new_count += 1

            print(f"    +{new_count} new (total: {len(all_dealers_raw)})")

        except Exception as exc:
            print(f"    Error: {exc}")

        time.sleep(1.5)

    # Fallback: try direct country-level query if low results
    if len(all_dealers_raw) < 5:
        print(f"\n  Low results — trying direct country query...")
        params_direct = {
            "brand": config["brand_code"],
            "country": "NL",
            "language": "nl",
            "limit": "500",
        }
        try:
            resp = requests.get(
                API_BASE, headers=HEADERS, params=params_direct, timeout=30
            )
            if resp.status_code == 200:
                data = resp.json()
                dealers_list = data if isinstance(data, list) else data.get("dealers", [])
                for dealer in dealers_list:
                    did = dealer.get("dealerId", dealer.get("id", ""))
                    if did and did not in seen_ids:
                        seen_ids.add(did)
                        all_dealers_raw.append(dealer)
                print(f"  Direct query added dealers (total: {len(all_dealers_raw)})")
        except Exception as exc:
            print(f"  Direct query error: {exc}")

    print(f"\n  Total unique {brand_name} dealers: {len(all_dealers_raw)}")
    return _process(all_dealers_raw, brand_name)


def _process(raw: list, brand_name: str) -> list:
    processed = []
    for d in raw:
        addr = d.get("address", {}) or {}
        geo = d.get("geoCoordinates", d.get("geo", {})) or {}
        contact = d.get("contact", {}) or {}

        # Services / activities
        activities = d.get("activities", d.get("services", [])) or []
        if isinstance(activities, list):
            svc_names = [
                a.get("label", a.get("name", a)) if isinstance(a, dict) else str(a)
                for a in activities
            ]
        else:
            svc_names = []

        street = addr.get("addressLine1", addr.get("street", ""))
        city = addr.get("city", "")
        zip_code = addr.get("zipCode", addr.get("postalCode", ""))

        processed.append(
            {
                "dealer_id": d.get("dealerId", d.get("id", "")),
                "brand": brand_name,
                "name": d.get("denomination", d.get("name", "")),
                "latitude": str(geo.get("latitude", geo.get("lat", ""))),
                "longitude": str(geo.get("longitude", geo.get("lng", ""))),
                "address_line_1": street,
                "address_line_2": addr.get("addressLine2", ""),
                "postal_code": zip_code,
                "city": city,
                "country_code": addr.get("countryCode", "NL"),
                "full_address": f"{street}, {zip_code} {city}".strip(", "),
                "phone": contact.get("phone", d.get("phone", "")),
                "email": contact.get("email", d.get("email", "")),
                "website": contact.get("website", d.get("url", "")),
                "products": " | ".join([s for s in svc_names if s]),
                "products_count": len(svc_names),
            }
        )
    return processed


def save_to_csv(dealers: list, brand_key: str) -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = os.path.join(os.path.dirname(__file__), "..", "output", brand_key)
    os.makedirs(output_dir, exist_ok=True)
    filename = os.path.join(output_dir, f"{brand_key}_dealers_nl_{timestamp}.csv")
    fieldnames = [
        "dealer_id", "brand", "name", "latitude", "longitude",
        "full_address", "address_line_1", "address_line_2",
        "postal_code", "city", "country_code",
        "phone", "email", "website", "products", "products_count",
    ]
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(dealers)
    print(f"  CSV saved: {filename}")
    return filename


def save_to_json(dealers: list, brand_key: str) -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = os.path.join(os.path.dirname(__file__), "..", "output", brand_key)
    os.makedirs(output_dir, exist_ok=True)
    filename = os.path.join(output_dir, f"{brand_key}_dealers_nl_{timestamp}.json")
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(dealers, f, ensure_ascii=False, indent=2)
    print(f"  JSON saved: {filename}")
    return filename


def main():
    import sys

    target_brands = sys.argv[1:] if len(sys.argv) > 1 else list(BRANDS.keys())
    invalid = [b for b in target_brands if b not in BRANDS]
    if invalid:
        print(f"Unknown brand(s): {invalid}. Valid: {list(BRANDS.keys())}")
        sys.exit(1)

    print("=" * 55)
    print("Renault Group Dealer Extractor — Netherlands (SALES ONLY)")
    print(f"Brands: {', '.join(target_brands)}")
    print("=" * 55)

    summary = []
    for bk in target_brands:
        dealers = extract_brand_dealers(bk)
        if dealers:
            save_to_csv(dealers, bk)
            save_to_json(dealers, bk)
        summary.append((BRANDS[bk]["name"], len(dealers)))

    print("\n" + "=" * 55)
    print("EXTRACTION SUMMARY")
    print("=" * 55)
    total = 0
    for brand_name, count in summary:
        print(f"  {brand_name:<15} {count:>4} dealers")
        total += count
    print(f"  {'TOTAL':<15} {total:>4} dealers")
    print("✓ Done!")


if __name__ == "__main__":
    main()
