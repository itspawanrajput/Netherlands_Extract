#!/usr/bin/env python3
"""
Multi-Brand Dealer Extractor — Netherlands (SALES ONLY)
Brands: Honda, Land Rover, Lexus, Mazda, Mitsubishi, Nissan, Polestar, Porsche, Smart, Suzuki, Tesla, Mini

Each brand uses its own API approach. This script handles all of them.
"""

import json
import csv
import os
from datetime import datetime
import requests
import time

NL_CITIES = [
    ("Amsterdam", 52.3676, 4.9041),
    ("Rotterdam", 51.9244, 4.4777),
    ("Den Haag", 52.0705, 4.3007),
    ("Utrecht", 52.0907, 5.1214),
    ("Eindhoven", 51.4416, 5.4697),
    ("Groningen", 53.2194, 6.5665),
    ("Tilburg", 51.5555, 5.0913),
    ("Breda", 51.5719, 4.7683),
    ("Nijmegen", 51.8426, 5.8546),
    ("Maastricht", 50.8514, 5.6910),
    ("Zwolle", 52.5168, 6.0830),
    ("Enschede", 52.2215, 6.8937),
    ("Leeuwarden", 53.2012, 5.7999),
    ("Middelburg", 51.4987, 3.6136),
    ("Almere", 52.3508, 5.2647),
]

DEFAULT_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


# ─────────────────────────────────────────────────────────────────────────────
# HONDA
# ─────────────────────────────────────────────────────────────────────────────
def extract_honda() -> list:
    """Honda uses a POST endpoint with multipart/form-data."""
    print("\n[Honda] Extracting...")
    url = "https://www.honda.nl/content/honda/nl_nl/cars/find-a-dealer/_jcr_content/fad2.dealers.JSON"
    headers = {
        "accept": "*/*",
        "origin": "https://www.honda.nl",
        "referer": "https://www.honda.nl/cars/find-a-dealer.html",
        "user-agent": DEFAULT_UA,
    }

    all_raw = []
    seen = set()

    for city, lat, lng in NL_CITIES:
        files = {
            "q": (None, city.lower()),
            "filters": (None, "SALES")
        }
        try:
            r = requests.post(url, headers=headers, files=files, timeout=30)
            if r.status_code == 200:
                data = r.json()
                # data is expected to be a list of { "dealer": { ... }, ... }
                new = 0
                for item in data:
                    dealer = item.get("dealer", {})
                    uid = dealer.get("uri", "")
                    if uid and uid not in seen:
                        seen.add(uid)
                        all_raw.append(dealer)
                        new += 1
                if new > 0:
                    print(f"  {city}: +{new} (total {len(all_raw)})")
            else:
                print(f"  {city} status: {r.status_code}")
        except Exception as e:
            print(f"  {city} error: {e}")
        time.sleep(1)

    return _normalise(all_raw, "Honda")


# ─────────────────────────────────────────────────────────────────────────────
# LAND ROVER (Jaguar Land Rover)
# ─────────────────────────────────────────────────────────────────────────────
def extract_land_rover() -> list:
    """JLR Dealer Locator API."""
    print("\n[Land Rover] Extracting...")
    # New global JLR API
    url = "https://retailerlocator.jaguarlandrover.com/dealers"
    headers = {
        "accept": "*/*",
        "referer": "https://www.landrover.nl/",
        "user-agent": DEFAULT_UA,
        "origin": "https://www.landrover.nl"
    }

    # Query directly for Amsterdam with a large 400km radius to get all of NL
    params = {
        "placeName": "Amsterdam, North Holland",
        "requestMarketLocale": "nl_nl",
        "brand": "Land Rover",
        "filter": "dealer",
        "radius": "400",
        "unitOfMeasure": "Kilometres",
        "country": "nl",
        "fetchOpeningTimes": "false"
    }

    all_raw = []
    seen = set()

    try:
        r = requests.get(url, headers=headers, params=params, timeout=30)
        if r.status_code == 200:
            data = r.json()
            dealers = data.get("dealers", [])
            new = 0
            for d in dealers:
                uid = d.get("ciCode", "")
                if uid and uid not in seen:
                    seen.add(uid)
                    all_raw.append(d)
                    new += 1
            print(f"  Found {new} dealers (total {len(all_raw)})")
        else:
            print(f"  Failed with status {r.status_code}")
    except Exception as e:
        print(f"  Error: {e}")

    return _normalise_jlr(all_raw, "Land Rover")



# ─────────────────────────────────────────────────────────────────────────────
# LEXUS
# ─────────────────────────────────────────────────────────────────────────────
def extract_lexus() -> list:
    """Lexus dealer locator for the Netherlands."""
    print("\n[Lexus] Extracting...")
    # Base URL uses {lon}/{lat}
    base_url = "https://kong-proxy-intranet.toyota-europe.com/dxp/dealers/api/lexus/nl/nl/drive"
    headers = {
        "accept": "*/*",
        "origin": "https://www.lexus.nl",
        "referer": "https://www.lexus.nl/dealers",
        "user-agent": DEFAULT_UA,
    }

    all_raw = []
    seen = set()

    # Amsterdam coordinates should cover to a wide limitSearchDistance, but we can loop through cities
    # since it's only 15 cities, to ensure complete coverage despite count limits.
    for city, lat, lng in NL_CITIES:
        url = f"{base_url}/{lng}/{lat}"
        params = {"count": "50"}
        try:
            r = requests.get(url, headers=headers, params=params, timeout=30)
            if r.status_code == 200:
                data = r.json()
                dealers = data.get("dealers", [])
                new = 0
                for d in dealers:
                    # Filter for sales dealers if necessary. Check 'services'
                    services = d.get("services", [])
                    svc_names = [s.get("service", "") for s in services]
                    if "ShowRoom" not in svc_names and "Sales" not in svc_names and "Showroom" not in svc_names:
                        continue
                        
                    uid = d.get("id", "")
                    if uid and uid not in seen:
                        seen.add(uid)
                        
                        addr = d.get("address", {})
                        geo = addr.get("geo", {}) or {}
                        
                        all_raw.append({
                            "dealer_id": uid,
                            "brand": "Lexus",
                            "name": d.get("name", ""),
                            "latitude": str(geo.get("lat", "")),
                            "longitude": str(geo.get("lon", "")),
                            "address_line_1": addr.get("address1", ""),
                            "address_line_2": addr.get("address2", ""),
                            "postal_code": addr.get("zip", ""),
                            "city": addr.get("city", ""),
                            "country_code": "NL",
                            "full_address": f"{addr.get('address1', '')}, {addr.get('zip', '')} {addr.get('city', '')}".strip(", "),
                            "phone": d.get("phone", ""),
                            "email": d.get("eMail", ""),
                            "website": d.get("url", ""),
                            "products": " | ".join(svc_names),
                            "products_count": len(svc_names),
                        })
                        new += 1
                print(f"  {city}: +{new} (total {len(all_raw)})")
            else:
                print(f"  {city} failed: {r.status_code}")
        except Exception as e:
            print(f"  {city} error: {e}")
        time.sleep(1)

    return all_raw


# ─────────────────────────────────────────────────────────────────────────────
# MAZDA
# ─────────────────────────────────────────────────────────────────────────────
def extract_mazda() -> list:
    """Mazda uses a REST API for dealer locations."""
    print("\n[Mazda] Extracting...")
    url = "https://www.mazda.nl/api/dealers"
    headers = {
        "Accept": "application/json",
        "Referer": "https://www.mazda.nl/forms/vind-een-dealer/",
        "User-Agent": DEFAULT_UA,
    }

    all_raw = []
    seen = set()

    try:
        r = requests.get(url, headers=headers, timeout=30)
        if r.status_code == 200:
            data = r.json()
            # The structure is {"data": {"dealers": [...]}}
            dealers = data.get("data", {}).get("dealers", [])
            new = 0
            for d in dealers:
                # Filter for "Car Sales"
                services = d.get("services", [])
                svc_names = [s.get("name", "") for s in services]
                if "Car Sales" not in svc_names:
                    continue

                uid = d.get("id", d.get("dealerCode", ""))
                if uid and uid not in seen:
                    seen.add(uid)
                    
                    addr = d.get("address", {})
                    geo = d.get("location", {}) or {}
                    
                    all_raw.append({
                        "dealer_id": uid,
                        "brand": "Mazda",
                        "name": d.get("name", ""),
                        "latitude": str(geo.get("latitude", "")),
                        "longitude": str(geo.get("longitude", "")),
                        "address_line_1": addr.get("address1", ""),
                        "address_line_2": addr.get("address2", ""),
                        "postal_code": addr.get("zip", ""),
                        "city": addr.get("city", ""),
                        "country_code": "NL",
                        "full_address": f"{addr.get('address1', '')}, {addr.get('zip', '')} {addr.get('city', '')}".strip(", "),
                        "phone": d.get("phoneNumber", ""),
                        "email": d.get("email", ""),
                        "website": d.get("website", ""),
                        "products": " | ".join(svc_names),
                        "products_count": len(svc_names),
                    })
                    new += 1
            print(f"  Found {new} sales dealers (total {len(all_raw)})")
        else:
            print(f"  Failed with status {r.status_code}")
    except Exception as e:
        print(f"  Error: {e}")

    return all_raw



# ─────────────────────────────────────────────────────────────────────────────
# MITSUBISHI
# ─────────────────────────────────────────────────────────────────────────────
def extract_mitsubishi() -> list:
    """Mitsubishi Netherlands dealer locator via GraphQL."""
    print("\n[Mitsubishi] Extracting...")
    url = "https://www-graphql.prod.mipulse.co/prod/graphql"
    headers = {
        "accept": "*/*",
        "accept-language": "en-IN,en-GB;q=0.9,en-US;q=0.8,en;q=0.7",
        "content-type": "application/json",
        "origin": "https://www.mitsubishi-motors.nl",
        "referer": "https://www.mitsubishi-motors.nl/",
        "user-agent": DEFAULT_UA,
    }

    payload = {
        "operationName": "searchDealer",
        "variables": {
            "latitude": 52.3675734,
            "longitude": 4.9041389,
            "service": "all",
            "filters": None,
            "radius": 400,
            "market": "nl",
            "language": "nl",
            "path": "/nl/nl/dealer-locator"
        },
        "extensions": {
            "persistedQuery": {
                "version": 1,
                "sha256Hash": "509a0311cd943cae03ef78f5964463ab328bdf08d72411ee4de7e41e01e5c793"
            }
        },
        "query": "query searchDealer($latitude: Float!, $longitude: Float!, $market: String!, $language: String!, $radius: Float!, $service: DepartmentCode, $filters: String, $path: String, $province: String) {\n  searchDealer(\n    path: $path\n    criteria: {latitude: $latitude, longitude: $longitude, market: $market, language: $language, radius: $radius, service: $service, filters: $filters, province: $province}\n  ) {\n    name\n    id\n    dealershipMarketId\n    url\n    carServiceCTA\n    testDriveCTA\n    dealerFilterTags\n    email\n    rating\n    logo\n    searchInventoryUrl\n    scheduleServiceUrl\n    phone {\n      phoneType\n      countryCode\n      areaCode\n      phoneNumber\n      extensionNumber\n      __typename\n    }\n    address {\n      addressLine1\n      addressLine2\n      addressLine3\n      postalArea\n      municipality\n      district\n      longitude\n      latitude\n      city\n      __typename\n    }\n    dealerDepartments {\n      name\n      code\n      email\n      phone {\n        phoneType\n        countryCode\n        areaCode\n        phoneNumber\n        extensionNumber\n        __typename\n      }\n      workingHours {\n        dayOfTheWeek\n        openTime\n        closeTime\n        status\n        __typename\n      }\n      __typename\n    }\n    __typename\n  }\n}\n"
    }

    all_raw = []
    seen = set()

    try:
        r = requests.post(url, headers=headers, json=payload, timeout=30)
        if r.status_code == 200:
            data = r.json()
            dealers = data.get("data", {}).get("searchDealer", [])
            for d in dealers:
                uid = str(d.get("id", ""))
                if uid and uid not in seen:
                    seen.add(uid)
                    
                    addr = d.get("address", {}) or {}
                    phone = d.get("phone", {}) or {}
                    
                    all_raw.append({
                        "dealer_id": uid,
                        "brand": "Mitsubishi",
                        "name": d.get("name", ""),
                        "latitude": str(addr.get("latitude", "")),
                        "longitude": str(addr.get("longitude", "")),
                        "address_line_1": addr.get("addressLine1", ""),
                        "address_line_2": addr.get("addressLine2", ""),
                        "postal_code": addr.get("postalArea", ""),
                        "city": addr.get("city", addr.get("district", addr.get("municipality", ""))),
                        "country_code": "NL",
                        "full_address": f"{addr.get('addressLine1', '')}, {addr.get('postalArea', '')} {addr.get('city', '')}".strip(", "),
                        "phone": phone.get("phoneNumber", ""),
                        "email": d.get("email", ""),
                        "website": d.get("url", ""),
                        "products": "Sales/Service",
                        "products_count": 1,
                    })
            print(f"  Found {len(all_raw)} dealers")
        else:
            print(f"  Failed with status {r.status_code}")
    except Exception as e:
        print(f"  Error: {e}")

    return all_raw

# ─────────────────────────────────────────────────────────────────────────────
# NISSAN
# ─────────────────────────────────────────────────────────────────────────────
def extract_nissan() -> list:
    """Nissan uses a central API with a Bearer token."""
    print("\n[Nissan] Extracting...")
    # Token provided by user, might be short-lived but useful for now.
    url = "https://eu.nissan-api.net/v2/dealers?size=-1&serviceFilterType=AND&include=openingHours%2Cdepartments"
    headers = {
        "Accept": "*/*",
        "Origin": "https://www.nissan.nl",
        "Referer": "https://www.nissan.nl/",
        "User-Agent": DEFAULT_UA,
        "accesstoken": "Bearer IAAFDitePfAUKZkwWSqWY0CDIRXC",
    }

    try:
        r = requests.get(url, headers=headers, timeout=30)
        if r.status_code == 200:
            data = r.json()
            dealers = data.get("dealers", [])
            # Filter for SALES (nl_nissan_VERKOOP)
            sales_dealers = []
            for d in dealers:
                services = [s.get("id", "") for s in d.get("services", [])]
                if "nl_nissan_VERKOOP" in services:
                    sales_dealers.append(d)
                elif "SALES" in str(services).upper():
                    sales_dealers.append(d)
            
            print(f"  Found {len(dealers)} total, {len(sales_dealers)} sales dealers.")
            return _normalise(sales_dealers, "Nissan")
        else:
            print(f"  Failed with status {r.status_code}")
    except Exception as e:
        print(f"  Error: {e}")

    return []


# ─────────────────────────────────────────────────────────────────────────────
# POLESTAR
# ─────────────────────────────────────────────────────────────────────────────
def extract_polestar() -> list:
    """Polestar retail locations API."""
    print("\n[Polestar] Extracting...")
    import bs4
    url_html = "https://www.polestar.com/nl/locations/"
    headers = {"User-Agent": DEFAULT_UA}
    
    try:
        r_html = requests.get(url_html, headers=headers, timeout=30)
        if r_html.status_code != 200:
            print(f"  Failed to get HTML: {r_html.status_code}")
            return []
            
        soup = bs4.BeautifulSoup(r_html.text, "html.parser")
        data_json = None
        for script in soup.find_all("script"):
            text = script.string
            if text and text.strip().startswith("window.__remixContext ="):
                data_str = text.strip()[len("window.__remixContext = "):]
                if data_str.endswith(";"):
                    data_str = data_str[:-1]
                data_json = json.loads(data_str)
                break
                
        if not data_json:
            print("  Could not find __remixContext in HTML")
            return []
            
        def get_keys(obj):
            found_ids = set()
            if isinstance(obj, dict):
                if 'mdmId' in obj:
                    found_ids.add(obj['mdmId'])
                for v in obj.values():
                    found_ids.update(get_keys(v))
            elif isinstance(obj, list):
                for item in obj:
                    found_ids.update(get_keys(item))
            return found_ids
            
        mdm_ids = list(get_keys(data_json))
        print(f"  Found {len(mdm_ids)} location IDs. Fetching details...")
        
        all_raw = []
        seen = set()
        
        chunk_size = 30
        for i in range(0, len(mdm_ids), chunk_size):
            chunk = mdm_ids[i:i+chunk_size]
            api_url = "https://www.polestar.com/buying-support/api/location-cards?locale=nl"
            for mdm_id in chunk:
                api_url += f"&ids={mdm_id}"
                
            r_api = requests.get(api_url, headers=headers, timeout=30)
            if r_api.status_code == 200:
                results = r_api.json().get("results", [])
                for d in results:
                    loc = d.get("locationDetail", {})
                    # For Polestar, check if it's a sales type or just include all.
                    uid = loc.get("mdmId", "")
                    if uid and uid not in seen:
                        seen.add(uid)
                        all_raw.append(loc)
            else:
                print(f"  Chunk fetch failed: {r_api.status_code}")
                
        return _normalise_polestar(all_raw)
        
    except Exception as e:
        print(f"  Error: {e}")
        return []


# ─────────────────────────────────────────────────────────────────────────────
# PORSCHE
# ─────────────────────────────────────────────────────────────────────────────
def extract_porsche() -> list:
    """Porsche dealer locator (new resources-nav.porsche.services API)."""
    print("\n[Porsche] Extracting...")
    # Using Amsterdam coordinates and 300km radius to cover the whole country in one go.
    url = "https://resources-nav.porsche.services/dealers/NL?coordinates=52.36757,4.90414&radius=300&unit=KM"
    headers = {
        "accept": "*/*",
        "origin": "https://www.porsche.com",
        "referer": "https://www.porsche.com/",
        "user-agent": DEFAULT_UA,
    }

    all_raw = []
    seen = set()

    try:
        r = requests.get(url, headers=headers, timeout=30)
        if r.status_code == 200:
            data = r.json()
            # The structure is a list of {"dealer": {...}, "distance": ...}
            for entry in data:
                d = entry.get("dealer", {})
                uid = d.get("id", d.get("porschePartnerNo", ""))
                if uid and uid not in seen:
                    seen.add(uid)
                    
                    addr = d.get("address", {})
                    contact = d.get("contactDetails", {})
                    
                    # Geometry is missing from the main dealer object in the snippet,
                    # but usually these APIs provide it. Let's check for it.
                    geo = d.get("location", {}) or {}
                    
                    all_raw.append({
                        "dealer_id": uid,
                        "brand": "Porsche",
                        "name": d.get("name", ""),
                        "latitude": str(geo.get("latitude", "")),
                        "longitude": str(geo.get("longitude", "")),
                        "address_line_1": addr.get("street", ""),
                        "address_line_2": "",
                        "postal_code": addr.get("postalCode", ""),
                        "city": addr.get("city", ""),
                        "country_code": addr.get("countryCode", "NL"),
                        "full_address": f"{addr.get('street', '')}, {addr.get('postalCode', '')} {addr.get('city', '')}".strip(", "),
                        "phone": contact.get("phoneNumber", ""),
                        "email": contact.get("emailAddress", ""),
                        "website": contact.get("homepage", ""),
                        "products": d.get("facilityType", "PORSCHE_CENTER"),
                        "products_count": 1,
                    })
            print(f"  Found {len(all_raw)} Porsche dealers")
        else:
            print(f"  Failed with status {r.status_code}")
    except Exception as e:
        print(f"  Error: {e}")

    return all_raw



# ─────────────────────────────────────────────────────────────────────────────
# SMART
# ─────────────────────────────────────────────────────────────────────────────
def extract_smart() -> list:
    """Smart dealer locator — Netherlands (bff/get-outlets API)."""
    print("\n[Smart] Extracting...")
    # Use Amsterdam coordinates and a high pageSize to get all dealers in NL
    url = "https://nl.smart.com/__app__/outlet-locator-app/prod/bff/get-outlets?envName=prod&preview=false&marketId=nl&language=nl&postalCode=00000&lat=52.37403&long=4.88969&crossCountrySearch=off&showMap=true&currentPage=1&pageSize=100&service=1"
    headers = {
        "accept": "*/*",
        "referer": "https://nl.smart.com/nl/dealer-locator/",
        "user-agent": DEFAULT_UA,
    }

    all_raw = []
    seen = set()

    try:
        r = requests.get(url, headers=headers, timeout=30)
        if r.status_code == 200:
            data = r.json()
            outlets = data.get("outlets", [])
            for d in outlets:
                uid = d.get("bpId", "")
                if uid and uid not in seen:
                    seen.add(uid)
                    
                    services = [str(s.get("serviceId", "")) for s in d.get("offeredService", [])]
                    
                    all_raw.append({
                        "dealer_id": uid,
                        "brand": "Smart",
                        "name": d.get("outlet", ""),
                        "latitude": str(d.get("lat", "")),
                        "longitude": str(d.get("lng", "")),
                        "address_line_1": d.get("street", ""),
                        "address_line_2": d.get("buildingNumber", "") or "",
                        "postal_code": d.get("postalCode", ""),
                        "city": d.get("city", ""),
                        "country_code": "NL",
                        "full_address": f"{d.get('street', '')} {d.get('buildingNumber', '') or ''}, {d.get('postalCode', '')} {d.get('city', '')}".replace(" ,", ",").strip(", "),
                        "phone": d.get("phone", ""),
                        "email": d.get("email", ""),
                        "website": f"https://nl.smart.com/nl/dealer-locator/{uid}",
                        "products": f"Services: {', '.join(services)}",
                        "products_count": len(services),
                    })
            print(f"  Found {len(all_raw)} Smart dealers")
        else:
            print(f"  Failed with status {r.status_code}")
    except Exception as e:
        print(f"  Error: {e}")

    return all_raw



# ─────────────────────────────────────────────────────────────────────────────
# SUZUKI
# ─────────────────────────────────────────────────────────────────────────────
def extract_suzuki() -> list:
    """Suzuki Netherlands dealer locator via prd API."""
    print("\n[Suzuki] Extracting...")
    # The API returns all dealers in one go
    url = "https://api.prd.suzuki.nl/v1/dealers/?brand=SUZUKI"
    headers = {
        "accept": "application/json",
        "referer": "https://www.suzuki.nl/",
        "user-agent": DEFAULT_UA,
    }

    all_raw = []
    seen = set()

    try:
        r = requests.get(url, headers=headers, timeout=30)
        if r.status_code == 200:
            data = r.json()
            # Filter for active sales dealers
            for d in data:
                if not d.get("is_active") or not d.get("is_sales_dealer"):
                    continue
                    
                uid = str(d.get("id", d.get("dealer_number", "")))
                if uid and uid not in seen:
                    seen.add(uid)
                    
                    street = d.get("street_name", "")
                    hno = d.get("house_number", "") or ""
                    zipcode = d.get("zipcode", "")
                    city = d.get("city", "")
                    
                    all_raw.append({
                        "dealer_id": uid,
                        "brand": "Suzuki",
                        "name": d.get("name", ""),
                        "latitude": str(d.get("location_lat", "")),
                        "longitude": str(d.get("location_long", "")),
                        "address_line_1": f"{street} {hno}".strip(),
                        "address_line_2": d.get("house_number_suffix", "") or "",
                        "postal_code": zipcode,
                        "city": city,
                        "country_code": "NL",
                        "full_address": f"{street} {hno}, {zipcode} {city}".strip(", "),
                        "phone": d.get("phone_number_sales", d.get("phone_number", "")),
                        "email": d.get("email_sales", d.get("email", "")),
                        "website": d.get("website", ""),
                        "products": "Sales & Service" if d.get("is_after_sales_dealer") else "Sales",
                        "products_count": 2 if d.get("is_after_sales_dealer") else 1,
                    })
            print(f"  Found {len(all_raw)} Suzuki sales dealers")
        else:
            print(f"  Failed with status {r.status_code}")
    except Exception as e:
        print(f"  Error: {e}")

    return all_raw



# ─────────────────────────────────────────────────────────────────────────────
# TESLA
# ─────────────────────────────────────────────────────────────────────────────
def extract_tesla() -> list:
    """Tesla stores and service centers in Netherlands using their public locations API."""
    print("\n[Tesla] Extracting...")
    url = "https://www.tesla.com/cua-api/tesla-locations"
    headers = {
        "accept": "application/json",
        "referer": "https://www.tesla.com/findus",
        "user-agent": DEFAULT_UA,
    }
    params = {
        "translate": "1",
        "usetrt": "1",
        "map_origin": "52.3676,4.9041",  # Amsterdam
        "range": "1000",
        "query": "store",  # SALES = store
        "region": "europe",
        "country": "NL",
        "types": "store",  # Sales stores only (not service)
    }

    all_raw = []
    try:
        r = requests.get(url, headers=headers, params=params, timeout=30)
        if r.status_code == 200:
            data = r.json()
            locations = data if isinstance(data, list) else data.get("results", [])
            # Filter to stores only (SALES)
            all_raw = [
                loc for loc in locations
                if "store" in loc.get("location_type", "").lower()
                or "store" in str(loc.get("type", "")).lower()
            ]
            print(f"  Found {len(all_raw)} Tesla stores (SALES)")
    except Exception as e:
        print(f"  Error: {e}")

    return _normalise_tesla(all_raw)


# ─────────────────────────────────────────────────────────────────────────────
# MINI (BMW Group)
# ─────────────────────────────────────────────────────────────────────────────
def extract_mini() -> list:
    """Mini (BMW Group) dealer locator for Netherlands via c2b-services."""
    print("\n[Mini] Extracting...")
    # The API returns all dealers in one go
    url = "https://c2b-services.bmw.com/c2b-localsearch/services/api/v4/clients/BMWSTAGE2_DLO/-/pois?brand=MINI&category=MI&language=nl&unit=km&cached=off&lat=0&lng=0&maxResults=700&showAll=true&country=NL"
    headers = {
        "accept": "application/json",
        "referer": "https://www.mini.nl/",
        "user-agent": DEFAULT_UA,
    }

    all_raw = []
    seen = set()

    try:
        r = requests.get(url, headers=headers, timeout=30)
        if r.status_code == 200:
            data = r.json()
            pois = data.get("data", {}).get("pois", [])
            for d in pois:
                uid = d.get("key", "")
                if uid and uid not in seen:
                    seen.add(uid)
                    
                    attrs = d.get("attributes", {})
                    
                    all_raw.append({
                        "dealer_id": uid,
                        "brand": "Mini",
                        "name": d.get("name", ""),
                        "latitude": str(d.get("lat", "")),
                        "longitude": str(d.get("lng", "")),
                        "address_line_1": d.get("street", ""),
                        "address_line_2": d.get("additionalStreet", "") or "",
                        "postal_code": d.get("postalCode", ""),
                        "city": d.get("city", ""),
                        "country_code": d.get("countryCode", "NL"),
                        "full_address": f"{d.get('street', '')}, {d.get('postalCode', '')} {d.get('city', '')}".strip(", "),
                        "phone": attrs.get("phone", ""),
                        "email": attrs.get("mail", ""),
                        "website": attrs.get("homepage", ""),
                        "products": d.get("category", "MINI"),
                        "products_count": 1,
                    })
            print(f"  Found {len(all_raw)} Mini dealers")
        else:
            print(f"  Failed with status {r.status_code}")
    except Exception as e:
        print(f"  Error: {e}")

    return all_raw



# ─────────────────────────────────────────────────────────────────────────────
# Normalisation helpers
# ─────────────────────────────────────────────────────────────────────────────
def _normalise(raw: list, brand_name: str) -> list:
    """Generic normaliser — handles common API shapes."""
    out = []
    for d in raw:
        addr = d.get("address", {}) or {}
        geo = (
            d.get("coordinates", {})
            or d.get("geoCoordinates", {})
            or d.get("geo", {})
            or {}
        )
        contact = d.get("contact", d.get("contacts", {})) or {}

        street = (
            addr.get("street", addr.get("addressLine1", addr.get("line1", "")))
        )
        city = addr.get("city", addr.get("town", ""))
        zip_code = addr.get("postalCode", addr.get("zipCode", addr.get("postCode", "")))

        lat = str(geo.get("latitude", geo.get("lat", d.get("latitude", d.get("lat", "")))))
        lng = str(geo.get("longitude", geo.get("lng", d.get("longitude", d.get("lng", "")))))

        phone = (
            contact.get("phone", contact.get("phoneNumber", ""))
            or d.get("phone", d.get("phoneNumber", ""))
        )
        email = contact.get("email", "") or d.get("email", "")
        website = (
            contact.get("website", contact.get("url", ""))
            or d.get("website", d.get("url", ""))
        )

        services = d.get("services", d.get("activities", d.get("features", []))) or []
        svc_names = [
            s.get("name", s.get("label", s.get("id", s.get("code", s)))) if isinstance(s, dict) else str(s)
            for s in services
        ]
        # Final safety check: ensure all names are strings
        svc_names = [str(s) if not isinstance(s, str) else s for s in svc_names]

        out.append({
            "dealer_id": d.get("id", d.get("dealerId", d.get("dealerCode", ""))),
            "brand": brand_name,
            "name": d.get("name", d.get("dealerName", d.get("title", ""))),
            "latitude": lat,
            "longitude": lng,
            "address_line_1": street,
            "address_line_2": addr.get("addressLine2", addr.get("line2", "")),
            "postal_code": zip_code,
            "city": city,
            "country_code": addr.get("countryCode", addr.get("country", "NL")),
            "full_address": f"{street}, {zip_code} {city}".strip(", "),
            "phone": phone,
            "email": email,
            "website": website,
            "products": " | ".join([s for s in svc_names if s]),
            "products_count": len(svc_names),
        })
    return out


def _normalise_jlr(raw: list, brand_name: str) -> list:
    out = []
    for d in raw:
        addr = d.get("address", {}) or {}
        
        # Pull first email/phone
        email = ""
        emails = d.get("emails", [])
        if emails and isinstance(emails, list):
            email = emails[0].get("contact", "")
            
        phone = ""
        phones = d.get("phoneNumbers", [])
        if phones and isinstance(phones, list):
            phone = phones[0].get("contact", "")
            
        out.append({
            "dealer_id": d.get("ciCode", d.get("id", "")),
            "brand": brand_name,
            "name": d.get("name", ""),
            "latitude": str(d.get("latitude", "")),
            "longitude": str(d.get("longitude", "")),
            "address_line_1": addr.get("line1", ""),
            "address_line_2": addr.get("line2", ""),
            "postal_code": addr.get("postCode", ""),
            "city": addr.get("town", ""),
            "country_code": addr.get("countryCode", "NL"),
            "full_address": f"{addr.get('line1', '')}, {addr.get('postCode', '')} {addr.get('town', '')}".strip(", "),
            "phone": phone,
            "email": email,
            "website": d.get("homePage", ""),
            "products": "Sales",
            "products_count": 1,
        })
    return out


def _normalise_polestar(raw: list) -> list:
    out = []
    for d in raw:
        if not isinstance(d, dict):
            continue
        out.append({
            "dealer_id": d.get("mdmId", d.get("id", "")),
            "brand": "Polestar",
            "name": d.get("name", ""),
            "latitude": str(d.get("latitude", "")),
            "longitude": str(d.get("longitude", "")),
            "address_line_1": d.get("address", d.get("street", "")),
            "address_line_2": "",
            "postal_code": d.get("postalCode", ""),
            "city": d.get("city", ""),
            "country_code": d.get("country", "NL"),
            "full_address": f"{d.get('address', '')}, {d.get('postalCode', '')} {d.get('city', '')}".strip(", "),
            "phone": d.get("phoneNumber", d.get("phone", "")),
            "email": d.get("email", ""),
            "website": "https://www.polestar.com/nl/locations/",
            "products": " | ".join(d.get("capabilities", [])),
            "products_count": len(d.get("capabilities", [])),
        })
    return out


def _normalise_tesla(raw: list) -> list:
    out = []
    for d in raw:
        addr = d.get("address", {}) or {}
        out.append({
            "dealer_id": d.get("id", d.get("nid", "")),
            "brand": "Tesla",
            "name": d.get("title", d.get("name", "")),
            "latitude": str(d.get("latitude", d.get("lat", ""))),
            "longitude": str(d.get("longitude", d.get("lng", ""))),
            "address_line_1": addr.get("street_address", d.get("address", "")),
            "address_line_2": "",
            "postal_code": addr.get("postal_code", ""),
            "city": addr.get("city", d.get("city", "")),
            "country_code": "NL",
            "full_address": d.get("address", ""),
            "phone": d.get("phone", ""),
            "email": d.get("email", ""),
            "website": d.get("path", ""),
            "products": "Sales Store",
            "products_count": 1,
        })
    return out


def _normalise_bmw(raw: list, brand_name: str) -> list:
    out = []
    for d in raw:
        addr = d.get("address", {}) or {}
        geo = d.get("geoCoordinates", d.get("geo", {})) or {}
        contact = d.get("contactDetails", d.get("contact", {})) or {}
        out.append({
            "dealer_id": d.get("id", d.get("outletId", "")),
            "brand": brand_name,
            "name": d.get("name", d.get("dealerName", "")),
            "latitude": str(geo.get("latitude", "")),
            "longitude": str(geo.get("longitude", "")),
            "address_line_1": addr.get("street", ""),
            "address_line_2": addr.get("addressLine2", ""),
            "postal_code": addr.get("zipCode", addr.get("postalCode", "")),
            "city": addr.get("city", ""),
            "country_code": addr.get("countryIsoCode", "NL"),
            "full_address": f"{addr.get('street', '')}, {addr.get('zipCode', '')} {addr.get('city', '')}".strip(", "),
            "phone": contact.get("phone", ""),
            "email": contact.get("email", ""),
            "website": contact.get("website", d.get("websiteUrl", "")),
            "products": " | ".join([a.get("type", "") for a in (d.get("activities", []) or [])]),
            "products_count": len(d.get("activities", [])),
        })
    return out


# ─────────────────────────────────────────────────────────────────────────────
# Save helpers
# ─────────────────────────────────────────────────────────────────────────────
FIELDNAMES = [
    "dealer_id", "brand", "name", "latitude", "longitude",
    "full_address", "address_line_1", "address_line_2",
    "postal_code", "city", "country_code",
    "phone", "email", "website", "products", "products_count",
]


def save(dealers: list, brand_key: str):
    if not dealers:
        print(f"  No data to save for {brand_key}")
        return
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = os.path.join(os.path.dirname(__file__), "..", "output", brand_key)
    os.makedirs(output_dir, exist_ok=True)

    csv_path = os.path.join(output_dir, f"{brand_key}_dealers_nl_{timestamp}.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(dealers)
    print(f"  CSV: {csv_path}  ({len(dealers)} records)")

    json_path = os.path.join(output_dir, f"{brand_key}_dealers_nl_{timestamp}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(dealers, f, ensure_ascii=False, indent=2)
    print(f"  JSON: {json_path}")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────
EXTRACTORS = {
    "honda": extract_honda,
    "land_rover": extract_land_rover,
    "lexus": extract_lexus,
    "mazda": extract_mazda,
    "mitsubishi": extract_mitsubishi,
    "nissan": extract_nissan,
    "polestar": extract_polestar,
    "porsche": extract_porsche,
    "smart": extract_smart,
    "suzuki": extract_suzuki,
    "tesla": extract_tesla,
    "mini": extract_mini,
}


def main():
    import sys

    target = sys.argv[1:] if len(sys.argv) > 1 else list(EXTRACTORS.keys())
    invalid = [b for b in target if b not in EXTRACTORS]
    if invalid:
        print(f"Unknown brand(s): {invalid}")
        print(f"Valid: {list(EXTRACTORS.keys())}")
        sys.exit(1)

    print("=" * 60)
    print("Multi-Brand Dealer Extractor — Netherlands (SALES ONLY)")
    print(f"Brands: {', '.join(target)}")
    print("=" * 60)

    summary = []
    for bk in target:
        try:
            dealers = EXTRACTORS[bk]()
            save(dealers, bk)
            summary.append((bk.title(), len(dealers)))
        except Exception as exc:
            print(f"  ERROR extracting {bk}: {exc}")
            import traceback; traceback.print_exc()
            summary.append((bk.title(), 0))

    print("\n" + "=" * 60)
    print("EXTRACTION SUMMARY")
    print("=" * 60)
    total = 0
    for brand_name, count in summary:
        print(f"  {brand_name:<15} {count:>4} dealers")
        total += count
    print(f"  {'TOTAL':<15} {total:>4} dealers")
    print("✓ All done!")


if __name__ == "__main__":
    main()
