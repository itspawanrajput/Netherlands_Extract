import json
import csv
import os
from datetime import datetime
from bs4 import BeautifulSoup

def parse_tesla_html():
    with open("tesla_nl.html", "r", encoding="utf-8") as f:
        html = f.read()

    soup = BeautifulSoup(html, "html.parser")
    script = soup.find("script", id="__NEXT_DATA__")
    if not script:
        print("Could not find __NEXT_DATA__ script tag.")
        return

    data = json.loads(script.string)
    locations = data.get("props", {}).get("pageProps", {}).get("data", [])
    
    processed = []
    for loc in locations:
        source = loc.get("_source", {})
        marketing = source.get("marketing", {})
        key_data = source.get("key_data", {})
        addr = key_data.get("address", {})
        
        name = marketing.get("display_name", loc.get("title", ""))
        # Only stores (Sales)
        if "sales" not in loc.get("location_type", []) and "store" not in str(loc.get("location_type", "")).lower():
            continue

        street = addr.get("address_1", "")
        city = addr.get("city", "")
        zip_code = addr.get("postal_code", "")
        
        processed.append({
            "dealer_id": loc.get("uuid", ""),
            "brand": "Tesla",
            "name": name,
            "latitude": str(loc.get("latitude", "")),
            "longitude": str(loc.get("longitude", "")),
            "address_line_1": street,
            "address_line_2": addr.get("address_2", ""),
            "postal_code": zip_code,
            "city": city,
            "country_code": "NL",
            "full_address": f"{street}, {zip_code} {city}".strip(", "),
            "phone": marketing.get("phone_numbers", ""),
            "email": "", # Not available in this JSON usually
            "website": f"https://www.tesla.com/findus/location/store/{loc.get('location_url_slug','')}",
            "products": "Sales Store",
            "products_count": 1,
        })

    print(f"Extracted {len(processed)} Tesla stores.")
    
    # Save
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = "output/tesla"
    os.makedirs(out_dir, exist_ok=True)
    
    csv_f = os.path.join(out_dir, f"tesla_dealers_nl_{ts}.csv")
    with open(csv_f, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=[
            "dealer_id", "brand", "name", "latitude", "longitude",
            "full_address", "address_line_1", "address_line_2",
            "postal_code", "city", "country_code",
            "phone", "email", "website", "products", "products_count"
        ])
        w.writeheader()
        w.writerows(processed)
    print(f"CSV → {csv_f}")
    
    json_f = os.path.join(out_dir, f"tesla_dealers_nl_{ts}.json")
    with open(json_f, "w", encoding="utf-8") as f:
        json.dump(processed, f, ensure_ascii=False, indent=2)
    print(f"JSON → {json_f}")

if __name__ == "__main__":
    parse_tesla_html()
