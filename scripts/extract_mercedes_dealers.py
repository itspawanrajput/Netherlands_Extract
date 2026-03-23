#!/usr/bin/env python3
"""
Mercedes-Benz Dealer Extractor — Netherlands (SALES ONLY)
Uses the DMS Plus API with NL-specific search profile and API key.

Confirmed working 2026-03-23:
- searchProfile: 0001_DLp-NL
- x-apikey: ce7d9916-6a3d-407a-b086-fea4cbae05f6
- marketCode: NL
- max 25 results/page, 250km radius per search
"""

import json
import csv
import os
from datetime import datetime
import requests
import time

BASE_URL = "https://api.oneweb.mercedes-benz.com/dms-plus/v3/api/dealers/location/id"
MARKET_URL = "https://api.oneweb.mercedes-benz.com/dms-plus/v3/api/dealers/market"

HEADERS = {
    "accept": "*/*",
    "accept-language": "en-US,en;q=0.9",
    "x-apikey": "ce7d9916-6a3d-407a-b086-fea4cbae05f6",
    "dlcorigin": "FE",
    "origin": "https://www.mercedes-benz.nl",
    "referer": "https://www.mercedes-benz.nl/passengercars/mercedes-benz-cars/dealer-locator.html/",
    "sec-ch-ua": '"Chromium";v="146", "Not-A.Brand";v="24", "Google Chrome";v="146"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"macOS"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "cross-site",
    "user-agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36"
    ),
}

# Dutch cities with Google Place IDs (used by the location/id endpoint)
NL_LOCATIONS = [
    ("Amsterdam",   "ChIJVXealLU_xkcRja_At0z9AGY"),
    ("Rotterdam",   "ChIJcU7DwJCEw0cRsh3jvGFPOfY"),
    ("Den Haag",    "ChIJGzE9DS1l4kARoZ-ItKnEFiY"),
    ("Utrecht",     "ChIJc-tSZvMFxkcRCMn2G_KCdHg"),
    ("Eindhoven",   "ChIJD00j_VhYxUcReRPmMJSMmDo"),
    ("Groningen",   "ChIJnWCFm3bYx0cRFpKhq_jnQDs"),
    ("Tilburg",     "ChIJqf5eGEjjxEcR7StV5YeAZ1o"),
    ("Almere",      "ChIJc_5bJitTx0cRSLwVg_pAbbc"),
    ("Breda",       "ChIJUTsJlhELxEcRiXYlzQMVWl4"),
    ("Nijmegen",    "ChIJY-J96HqFxEcRhagV2H7nqrw"),
    ("Maastricht",  "ChIJzc3HMM-Wx0cRFhTJL1g5GRs"),
    ("Zwolle",      "ChIJe2YCOO1tx0cRhxHQFhkRFaQ"),
    ("Enschede",    "ChIJpaXbqEbHwkcRhyoJV4m4pUA"),
    ("Leeuwarden",  "ChIJKyBEfawUx0cRGQ_vD37sE8g"),
    ("Middelburg",  "ChIJcWX3d9Jyx0cRDVFLN-xqvxA"),
]


def extract_dealers() -> list:
    print("Mercedes-Benz Dealer Extractor — Netherlands (SALES ONLY)")
    print(f"Strategy: market-wide sweep + {len(NL_LOCATIONS)}-city geo search\n")

    all_dealers_raw = []
    seen_outlet_ids = set()

    # ── Step 1: Market-wide sweep (gets all NL outlets in one call) ──────────
    print("Step 1: Market-wide sweep...")
    params_market = {
        "marketCode": "NL",
        "searchProfile": "0001_DLp-NL",
        "page": "1",
        "size": "250",
        "includeFields": "*",
        "localeLanguage": "false",
    }
    page = 1
    while page <= 20:
        params_market["page"] = str(page)
        try:
            r = requests.get(MARKET_URL, headers=HEADERS, params=params_market, timeout=30)
            if r.status_code != 200:
                print(f"  Market sweep HTTP {r.status_code} on page {page}")
                break
            data = r.json()
            dealers = data.get("dealers", [])
            if not dealers:
                break
            for d in dealers:
                oid = d.get("outletId", "")
                if oid and oid not in seen_outlet_ids:
                    seen_outlet_ids.add(oid)
                    all_dealers_raw.append(d)
            print(f"  Page {page}: +{len(dealers)} (total: {len(all_dealers_raw)})")
            if len(dealers) < 250:
                break
            page += 1
            time.sleep(0.5)
        except Exception as e:
            print(f"  Market page {page} error: {e}")
            break

    print(f"  Market sweep total: {len(all_dealers_raw)} unique dealers")

    # ── Step 2: Geo-city sweep (catches any missed by market endpoint) ────────
    print("\nStep 2: Geo-city search (deduplication applied)...")
    for city_name, location_id in NL_LOCATIONS:
        params = {
            "marketCode": "NL",
            "searchProfile": "0001_DLp-NL",
            "page": "1",
            "size": "25",
            "includeFields": "*",
            "localeLanguage": "false",
            "strictGeo": "true",
            "expand": "false",
            "includeApplicants": "true",
            "locationId": location_id,
            "distance": "250",
            "unit": "km",
        }

        page = 1
        city_new = 0
        while page <= 50:
            params["page"] = str(page)
            try:
                r = requests.get(BASE_URL, headers=HEADERS, params=params, timeout=30)
                if r.status_code in (429, 503):
                    wait = 60
                    print(f"  {city_name}: rate limited ({r.status_code}) — waiting {wait}s...")
                    time.sleep(wait)
                    continue
                if r.status_code != 200:
                    if page == 1:
                        print(f"  {city_name}: HTTP {r.status_code}")
                    break
                dealers = r.json().get("dealers", [])
                if not dealers:
                    break
                for d in dealers:
                    oid = d.get("outletId", "")
                    if oid and oid not in seen_outlet_ids:
                        seen_outlet_ids.add(oid)
                        all_dealers_raw.append(d)
                        city_new += 1
                if len(dealers) < 25:
                    break
                page += 1
                time.sleep(0.5)
            except Exception as e:
                print(f"  {city_name} page {page} error: {e}")
                break

        if city_new:
            print(f"  {city_name}: +{city_new} new (total: {len(all_dealers_raw)})")
        time.sleep(5)  # larger pause between cities to avoid rate limiting

    print(f"\nTotal unique Mercedes-Benz NL dealers: {len(all_dealers_raw)}")
    return _process(all_dealers_raw)


def _process(raw: list) -> list:
    processed = []
    for dealer in raw:
        outlet_id = dealer.get("outletId", dealer.get("companyId", ""))
        legal_name = dealer.get("legalName", "")
        name_addition = dealer.get("nameAddition", "")
        dealer_name = name_addition if name_addition else legal_name

        address = dealer.get("address", {})
        coords  = address.get("coordinates", {})
        street_full = f"{address.get('street', '')} {address.get('streetNumber', '')}".strip()
        city     = address.get("city", "")
        zip_code = address.get("zipCode", "")
        country  = address.get("country", "NL")

        services_list = dealer.get("services", []) or []
        products, phone, email, website = [], "", "", ""
        for svc in services_list:
            svc_info = svc.get("service", {})
            svc_name = svc_info.get("name", "")
            if svc_name:
                products.append(svc_name)
            comm = svc.get("communication", {}) or {}
            if not email   and "EMAIL"    in comm: email   = comm["EMAIL"]
            if not website and "INTERNET" in comm: website = comm["INTERNET"]
            if not phone   and "PHONE"    in comm: phone   = comm["PHONE"]

        processed.append({
            "dealer_id":    outlet_id,
            "brand":        "Mercedes",
            "company_id":   dealer.get("companyId", ""),
            "name":         dealer_name,
            "legal_name":   legal_name,
            "latitude":     str(coords.get("latitude", "")),
            "longitude":    str(coords.get("longitude", "")),
            "address_line_1": street_full,
            "address_line_2": address.get("district", ""),
            "postal_code":  zip_code,
            "city":         city,
            "country_code": country,
            "region":       address.get("region", {}).get("state", ""),
            "province":     address.get("region", {}).get("province", ""),
            "full_address": f"{street_full}, {zip_code} {city}".strip(", "),
            "phone":        phone,
            "email":        email,
            "website":      website,
            "products":     " | ".join(products),
            "products_count": len(products),
            "affiliate":    dealer.get("affiliate", False),
            "main_outlet":  dealer.get("mainOutlet", False),
        })
    return processed


def _save(dealers: list) -> None:
    if not dealers:
        print("No Mercedes dealers to save.")
        return
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = os.path.join(os.path.dirname(__file__), "..", "output", "mercedes")
    os.makedirs(out_dir, exist_ok=True)

    fieldnames = [
        "dealer_id", "brand", "company_id", "name", "legal_name",
        "latitude", "longitude", "full_address", "address_line_1", "address_line_2",
        "postal_code", "city", "country_code", "region", "province",
        "phone", "email", "website", "products", "products_count",
        "affiliate", "main_outlet",
    ]
    csv_f = os.path.join(out_dir, f"mercedes_dealers_nl_{ts}.csv")
    with open(csv_f, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader(); w.writerows(dealers)
    print(f"CSV  → {csv_f}  ({len(dealers)} records)")

    json_f = os.path.join(out_dir, f"mercedes_dealers_nl_{ts}.json")
    with open(json_f, "w", encoding="utf-8") as f:
        json.dump(dealers, f, ensure_ascii=False, indent=2)
    print(f"JSON → {json_f}")


def main():
    print("=" * 60)
    print("Mercedes-Benz Dealer Extractor — Netherlands (SALES ONLY)")
    print("=" * 60)
    dealers = extract_dealers()
    if dealers:
        s = dealers[0]
        print(f"\nSample: {s['name']} | {s['full_address']} | {s['phone']}")
    _save(dealers)
    print(f"\n✓ Done! {len(dealers)} Mercedes dealers extracted.")


if __name__ == "__main__":
    main()
