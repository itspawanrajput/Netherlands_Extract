#!/usr/bin/env python3
"""
VW Group Dealer Extractor — Netherlands (SALES ONLY)
Brands: Audi, CUPRA, SEAT
Uses the VW Group PSS GraphQL API (graphql.pss.audi.com).
"""

import json
import csv
import os
from datetime import datetime
import requests
import time

# PSS GraphQL endpoint used by VW Group brands
GRAPHQL_URL = "https://graphql.pss.audi.com/"

# Each brand uses a distinct clientid header
BRANDS = {
    "audi": {
        "name": "Audi",
        "client_id": "d7sfqwrxzu",
        "country": "NL",
        "language": "nl",
        "market_code": "nl",
    },
    "cupra": {
        "name": "CUPRA",
        "client_id": "cupranl",
        "country": "NL",
        "language": "nl",
        "market_code": "nl",
    },
    "seat": {
        "name": "SEAT",
        "client_id": "seatnl",
        "country": "NL",
        "language": "nl",
        "market_code": "nl",
    },
}

# Netherlands search terms (cities + postcodes)
NL_SEARCH_TERMS = [
    "Amsterdam",
    "Rotterdam",
    "Den Haag",
    "Utrecht",
    "Eindhoven",
    "Groningen",
    "Tilburg",
    "Almere",
    "Breda",
    "Nijmegen",
    "Maastricht",
    "Zwolle",
    "Enschede",
    "Haarlem",
    "Arnhem",
]

# GraphQL query — fetches dealers by search term, filtered to SALES activity
DEALER_QUERY = """
query Dealer($searchTerm: String!, $market: String!, $language: String!, $activities: [String]) {
  dealersByTerm(
    searchTerm: $searchTerm
    market: $market
    language: $language
    activities: $activities
    radius: 150
    maxResults: 50
  ) {
    dealers {
      dealerId
      name
      address {
        street
        houseNumber
        zipCode
        city
        countryCode
      }
      geoCoordinates {
        latitude
        longitude
      }
      services {
        id
        name
      }
      contact {
        phone
        email
        website
      }
    }
  }
}
"""


def extract_brand_dealers(brand_key: str) -> list:
    config = BRANDS[brand_key]
    brand_name = config["name"]

    print(f"\n{'=' * 55}")
    print(f"Extracting {brand_name} dealers (Netherlands, SALES ONLY)...")
    print(f"{'=' * 55}")

    headers = {
        "Content-Type": "application/json",
        "clientid": config["client_id"],
        "Origin": f"https://www.{brand_key}.nl",
        "Referer": f"https://www.{brand_key}.nl/",
        "user-agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
    }

    all_dealers_raw = []
    seen_ids = set()

    for search_term in NL_SEARCH_TERMS:
        print(f"  Searching: {search_term}...")

        payload = {
            "operationName": "Dealer",
            "query": DEALER_QUERY,
            "variables": {
                "searchTerm": search_term,
                "market": config["market_code"],
                "language": config["language"],
                "activities": ["SALES"],  # SALES ONLY
            },
        }

        try:
            resp = requests.post(
                GRAPHQL_URL, headers=headers, json=payload, timeout=30
            )

            if resp.status_code != 200:
                print(f"    HTTP {resp.status_code} — skipping")
                time.sleep(2)
                continue

            data = resp.json()
            dealers_list = (
                data.get("data", {})
                .get("dealersByTerm", {})
                .get("dealers", [])
            )

            new_count = 0
            for dealer in dealers_list:
                did = dealer.get("dealerId", "")
                if did and did not in seen_ids:
                    seen_ids.add(did)
                    all_dealers_raw.append(dealer)
                    new_count += 1

            print(f"    +{new_count} new (total: {len(all_dealers_raw)})")

        except Exception as exc:
            print(f"    Error: {exc}")

        time.sleep(1.5)

    print(f"\n  Total unique {brand_name} dealers: {len(all_dealers_raw)}")
    return _process(all_dealers_raw, brand_name)


def _process(raw: list, brand_name: str) -> list:
    processed = []
    for d in raw:
        addr = d.get("address", {})
        geo = d.get("geoCoordinates", {})
        contact = d.get("contact", {}) or {}
        services = d.get("services", []) or []

        street = addr.get("street", "")
        house_no = addr.get("houseNumber", "")
        full_street = f"{street} {house_no}".strip()
        city = addr.get("city", "")
        zip_code = addr.get("zipCode", "")

        processed.append(
            {
                "dealer_id": d.get("dealerId", ""),
                "brand": brand_name,
                "name": d.get("name", ""),
                "latitude": str(geo.get("latitude", "")),
                "longitude": str(geo.get("longitude", "")),
                "address_line_1": full_street,
                "address_line_2": "",
                "postal_code": zip_code,
                "city": city,
                "country_code": addr.get("countryCode", "NL"),
                "full_address": f"{full_street}, {zip_code} {city}".strip(", "),
                "phone": contact.get("phone", ""),
                "email": contact.get("email", ""),
                "website": contact.get("website", ""),
                "products": " | ".join(
                    [s.get("name", "") for s in services if s.get("name")]
                ),
                "products_count": len(services),
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
    print("VW Group Dealer Extractor — Netherlands (SALES ONLY)")
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
