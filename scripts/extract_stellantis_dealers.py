#!/usr/bin/env python3
"""
Stellantis Brands Dealer Data Extractor - Netherlands
Extracts SALES ONLY dealers for: Alfa Romeo, Citroen, DS, Fiat, Jeep, Lancia, Opel, Peugeot.
Handles both PSA-legacy (DealersServlet) and FCA-legacy (Fiat DealerLocator) systems.

Confirmed working 2026-03-23.
"""

import json
import csv
import os
import re
from datetime import datetime
import requests
import time

# Brands using the PSA-legacy DealersServlet
PSA_BRANDS = {
    "citroen": {
        "name": "Citroen",
        "url": "https://www.citroen.nl/apps/atomic/DealersServlet",
        "path": "L2NvbnRlbnQvY2l0cm9lbi93b3JsZHdpZGUvbmV0aGVybGFuZHMvbmw=",
        "referer": "https://www.citroen.nl/handige-links/dealer.html",
    },
    "peugeot": {
        "name": "Peugeot",
        "url": "https://www.peugeot.nl/apps/atomic/DealersServlet",
        "path": "L2NvbnRlbnQvcGV1Z2VvdC93b3JsZHdpZGUvbmV0aGVybGFuZHMvbmw=",
        "referer": "https://www.peugeot.nl/handige-links/dealer.html",
    },
    "ds": {
        "name": "DS",
        "url": "https://www.dsautomobiles.nl/apps/atomic/DealersServlet",
        "path": "L2NvbnRlbnQvZHMvd29ybGR3aWRlL25ldGhlcmxhbmRzL25s",
        "referer": "https://www.dsautomobiles.nl/handige-links/dealer.html",
    },
    "opel": {
        "name": "Opel",
        "url": "https://www.opel.nl/apps/atomic/DealersServlet",
        "path": "L2NvbnRlbnQvb3BlbC93b3JsZHdpZGUvbmV0aGVybGFuZHMvbmxfTkw=",
        "referer": "https://www.opel.nl/tools/opel-dealer-zoeken.html",
    },
}

# Brands using the FCA-legacy Fiat DealerLocator
FCA_BRANDS = {
    "fiat": {
        "name": "Fiat",
        "brand_code": "00",
        "referer": "https://www.fiat.nl/",
    },
    "lancia": {
        "name": "Lancia",
        "brand_code": "70",
        "referer": "https://www.lancia.nl/",
    },
    "jeep": {
        "name": "Jeep",
        "brand_code": "57",
        "referer": "https://www.jeep.nl/",
    },
    "alfa_romeo": {
        "name": "Alfa Romeo",
        "brand_code": "83",
        "referer": "https://www.alfaromeo.nl/",
    },
}

BRANDS = {**PSA_BRANDS, **FCA_BRANDS}

# 20 Dutch cities for geo search
NL_LOCATIONS = [
    {"city": "Amsterdam",   "lat": 52.37308, "lng": 4.89245},
    {"city": "Rotterdam",   "lat": 51.9225,  "lng": 4.47917},
    {"city": "Utrecht",     "lat": 52.09083, "lng": 5.12222},
    {"city": "Eindhoven",   "lat": 51.44083, "lng": 5.47778},
    {"city": "Groningen",   "lat": 53.21917, "lng": 6.56667},
    {"city": "Tilburg",     "lat": 51.55556, "lng": 5.09139},
    {"city": "Breda",       "lat": 51.58667, "lng": 4.77583},
    {"city": "Maastricht",  "lat": 50.84833, "lng": 5.68889},
    {"city": "Zwolle",      "lat": 52.5125,  "lng": 6.09444},
    {"city": "Enschede",    "lat": 52.21833, "lng": 6.89583},
    {"city": "Leeuwarden",  "lat": 53.20139, "lng": 5.80861},
    {"city": "Middelburg",  "lat": 51.5,     "lng": 3.61333},
    {"city": "Apeldoorn",   "lat": 52.21,    "lng": 5.97},
    {"city": "Arnhem",      "lat": 51.98,    "lng": 5.91},
    {"city": "Nijmegen",    "lat": 51.84,    "lng": 5.85},
    {"city": "Heerenveen",  "lat": 52.96,    "lng": 5.92},
    {"city": "Alkmaar",     "lat": 52.63,    "lng": 4.75},
    {"city": "Den Helder",  "lat": 52.95,    "lng": 4.76},
    {"city": "Venlo",       "lat": 51.37,    "lng": 6.17},
    {"city": "Roermond",    "lat": 51.19,    "lng": 5.99},
]


def _headers(referer: str) -> dict:
    return {
        "Accept": "application/json, text/plain, */*",
        "Referer": referer,
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36"
        ),
    }


def extract_psa_brand(brand_key: str, config: dict) -> list:
    """Extract using DealersServlet (PSA style)."""
    brand_name = config["name"]
    print(f"  Extracting {brand_name} (PSA system)...")
    
    seen = set()
    all_raw = []
    
    for loc in NL_LOCATIONS:
        params = {
            "distance": "50",
            "maxResults": "40",
            "orderResults": "false",
            "path": config["path"],
            "searchTerm": loc["city"],
            "searchType": "city",
        }
        
        # Opel needs extra parameters
        if brand_key == "opel":
            params.update({
                "isAutocompleteUsed": "true",
                "lat": str(loc["lat"]),
                "lng": str(loc["lng"]),
                "searchTerm": loc["city"] + ", Nederland"
            })

        try:
            r = requests.get(config["url"], headers=_headers(config["referer"]), params=params, timeout=30)
            if r.status_code != 200:
                print(f"    {loc['city']}: HTTP {r.status_code}")
                continue

            dealers_raw = r.json().get("payload", {}).get("dealers", []) or []
            new_count = 0
            for d in dealers_raw:
                # SALES filter
                services = d.get("services", []) or []
                if not any(s.get("type", "").lower() == "sales" for s in services):
                    continue
                
                uid = d.get("siteGeo") or d.get("rrdi") or (d.get("dealerName", "") + d.get("address", {}).get("postalCode", ""))
                if uid and uid not in seen:
                    seen.add(uid)
                    all_raw.append(d)
                    new_count += 1
            if new_count > 0:
                print(f"    {loc['city']}: +{new_count} (total: {len(all_raw)})")
        except Exception as e:
            print(f"    {loc['city']}: Error {e}")
        time.sleep(1)
        
    return _process_psa_dealers(all_raw, brand_name)


def _process_psa_dealers(raw_list: list, brand_name: str) -> list:
    processed = []
    for d in raw_list:
        addr = d.get("address", {}) or {}
        geo = d.get("geolocation", {}) or {}
        contact = d.get("generalContact", {}) or {}
        services = d.get("services", []) or []
        
        street = addr.get("addressLine1", "")
        city = addr.get("cityName", "")
        zip_code = addr.get("postalCode", "")
        
        processed.append({
            "dealer_id": d.get("siteGeo", d.get("rrdi", "")),
            "brand": brand_name,
            "name": d.get("dealerName", ""),
            "latitude": str(geo.get("latitude", "")),
            "longitude": str(geo.get("longitude", "")),
            "address_line_1": street,
            "address_line_2": addr.get("addressLine2", ""),
            "postal_code": zip_code,
            "city": city,
            "country_code": "NL",
            "full_address": f"{street}, {zip_code} {city}".strip(", "),
            "phone": contact.get("phone1", ""),
            "email": contact.get("email", ""),
            "website": d.get("dealerUrl") or "",
            "products": " | ".join([s.get("name", "") for s in services if s.get("name")]),
            "products_count": len(services),
        })
    return processed


def extract_fca_brand(brand_key: str, config: dict) -> list:
    """Extract using Fiat DealerLocator (FCA style)."""
    brand_name = config["name"]
    print(f"  Extracting {brand_name} (FCA system)...")
    
    seen = set()
    all_raw = []
    url = "https://dealerlocator.fiat.com/geocall/RestServlet"
    
    for loc in NL_LOCATIONS:
        params = {
            "jsonp": "callback",
            "mkt": "3122",
            "brand": config["brand_code"],
            "func": "finddealerxml",
            "serv": "sales",
            "track": "1",
            "x": str(loc["lng"]),
            "y": str(loc["lat"]),
            "rad": "99", # Must be < 100
        }
        
        try:
            r = requests.get(url, headers=_headers(config["referer"]), params=params, timeout=30)
            if r.status_code != 200:
                print(f"    {loc['city']}: HTTP {r.status_code}")
                continue
            
            # Extract JSON from JSONP callback
            text = r.text
            start = text.find("{")
            end = text.rfind("}")
            if start == -1 or end == -1:
                continue
                
            data = json.loads(text[start:end+1])
            dealers_raw = data.get("results", []) or []
            
            new_count = 0
            for d in dealers_raw:
                # Unique ID: MAINCODE or SITECODE + ZIPCODE
                uid = d.get("MAINCODE") or (d.get("COMPANYNAM", "") + d.get("ZIPCODE", ""))
                if uid and uid not in seen:
                    seen.add(uid)
                    all_raw.append(d)
                    new_count += 1
            if new_count > 0:
                print(f"    {loc['city']}: +{new_count} (total: {len(all_raw)})")
        except Exception as e:
            print(f"    {loc['city']}: Error {e}")
        time.sleep(1)
        
    return _process_fca_dealers(all_raw, brand_name)


def _process_fca_dealers(raw_list: list, brand_name: str) -> list:
    processed = []
    for d in raw_list:
        street = d.get("LEGAL_ADDRESS", "")
        city = d.get("LEGAL_TOWN", "")
        zip_code = d.get("ZIPCODE", "")
        
        processed.append({
            "dealer_id": d.get("MAINCODE", d.get("SITECODE", "")),
            "brand": brand_name,
            "name": d.get("COMPANYNAM", ""),
            "latitude": str(d.get("YCOORD", "")),
            "longitude": str(d.get("XCOORD", "")),
            "address_line_1": street,
            "address_line_2": "",
            "postal_code": zip_code,
            "city": city,
            "country_code": "NL",
            "full_address": f"{street}, {zip_code} {city}".strip(", "),
            "phone": d.get("TEL_1", ""),
            "email": d.get("GENERAL_EMAIL", ""),
            "website": d.get("WEBSITE", ""),
            "products": "Sales",
            "products_count": 1,
        })
    return processed


def save(dealers: list, brand_key: str):
    if not dealers:
        return
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = os.path.join(os.path.dirname(__file__), "..", "output", brand_key)
    os.makedirs(out_dir, exist_ok=True)
    
    # CSV
    csv_f = os.path.join(out_dir, f"{brand_key}_dealers_nl_{ts}.csv")
    with open(csv_f, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=[
            "dealer_id", "brand", "name", "latitude", "longitude",
            "full_address", "address_line_1", "address_line_2",
            "postal_code", "city", "country_code",
            "phone", "email", "website", "products", "products_count"
        ])
        w.writeheader()
        w.writerows(dealers)
    print(f"    CSV → {csv_f}")
    
    # JSON
    json_f = os.path.join(out_dir, f"{brand_key}_dealers_nl_{ts}.json")
    with open(json_f, "w", encoding="utf-8") as f:
        json.dump(dealers, f, ensure_ascii=False, indent=2)
    print(f"    JSON → {json_f}")


def main():
    import sys
    targets = sys.argv[1:] if len(sys.argv) > 1 else list(BRANDS.keys())
    
    print("=" * 60)
    print("Stellantis Dealer Extractor - Netherlands (SALES ONLY)")
    print("=" * 60)
    
    summary = []
    for bk in targets:
        if bk not in BRANDS:
            print(f"Unknown brand: {bk}")
            continue
            
        if bk in PSA_BRANDS:
            dealers = extract_psa_brand(bk, PSA_BRANDS[bk])
        else:
            dealers = extract_fca_brand(bk, FCA_BRANDS[bk])
            
        save(dealers, bk)
        summary.append((BRANDS[bk]["name"], len(dealers)))
        
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for name, count in summary:
        print(f"  {name:<15}: {count} dealers")
    print("=" * 60)


if __name__ == "__main__":
    main()
