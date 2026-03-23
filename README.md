# Netherlands Dealer Data Extraction

## Overview

Extracts **SALES ONLY** dealer sites in the **Netherlands** for **26 car brands**.

### Brands Covered

| # | Brand | Platform | Script |
|---|-------|----------|--------|
| 1 | Alfa Romeo | Stellantis | `extract_stellantis_dealers.py` |
| 2 | Alpine | Renault Group | `extract_renault_group_dealers.py` |
| 3 | Audi | VW Group PSS | `extract_vwgroup_dealers.py` |
| 4 | Citroen | Stellantis | `extract_stellantis_dealers.py` |
| 5 | CUPRA | VW Group PSS | `extract_vwgroup_dealers.py` |
| 6 | Dacia | Renault Group | `extract_renault_group_dealers.py` |
| 7 | DS | Stellantis | `extract_stellantis_dealers.py` |
| 8 | Fiat | Stellantis | `extract_stellantis_dealers.py` |
| 9 | Honda | Honda REST API | `extract_other_brands_dealers.py` |
| 10 | Jeep | Stellantis | `extract_stellantis_dealers.py` |
| 11 | Lancia | Stellantis | `extract_stellantis_dealers.py` |
| 12 | Land Rover | JLR API | `extract_other_brands_dealers.py` |
| 13 | Lexus | Lexus REST API | `extract_other_brands_dealers.py` |
| 14 | Mazda | Mazda EU REST API | `extract_other_brands_dealers.py` |
| 15 | Mercedes | DMS Plus API | `extract_mercedes_dealers.py` |
| 16 | Mini | BMW Group API | `extract_other_brands_dealers.py` |
| 17 | Mitsubishi | Mitsubishi REST API | `extract_other_brands_dealers.py` |
| 18 | Nissan | Nissan NL API | `extract_other_brands_dealers.py` |
| 19 | Opel | Stellantis | `extract_stellantis_dealers.py` |
| 20 | Peugeot | Stellantis | `extract_stellantis_dealers.py` |
| 21 | Polestar | Polestar GraphQL | `extract_other_brands_dealers.py` |
| 22 | Porsche | Porsche Finder API | `extract_other_brands_dealers.py` |
| 23 | SEAT | VW Group PSS | `extract_vwgroup_dealers.py` |
| 24 | Smart | Smart REST API | `extract_other_brands_dealers.py` |
| 25 | Suzuki | Suzuki NL API | `extract_other_brands_dealers.py` |
| 26 | Tesla | Tesla Locations API | `extract_other_brands_dealers.py` |

---

## Exclusions (as per brief)
- ❌ Default brands (already extracted)
- ❌ Chinese brands (separate ticket)
- ❌ Brands with < 100 registrations in past 12 months

---

## Setup

```bash
cd Netherlands_Extract

# (Recommended) Using uv
uv pip install -r requirements.txt

# Or traditional venv
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## Running the Scripts

### Run ALL 26 brands at once
```bash
uv run python scripts/run_all.py
# or
python scripts/run_all.py
```

### Run a specific brand group
```bash
python scripts/run_all.py stellantis     # Alfa Romeo, Citroën, DS, Fiat, Jeep, Lancia, Opel, Peugeot
python scripts/run_all.py vwgroup        # Audi, CUPRA, SEAT
python scripts/run_all.py renault        # Alpine, Dacia
python scripts/run_all.py mercedes       # Mercedes
python scripts/run_all.py other          # Honda, Land Rover, Lexus, Mazda, ...
```

### Run individual brands
```bash
# Stellantis brands (pass brand key as argument)
python scripts/extract_stellantis_dealers.py alfa_romeo
python scripts/extract_stellantis_dealers.py citroen peugeot opel  # multiple

# VW Group brands
python scripts/extract_vwgroup_dealers.py audi
python scripts/extract_vwgroup_dealers.py cupra seat

# Renault Group brands
python scripts/extract_renault_group_dealers.py dacia
python scripts/extract_renault_group_dealers.py alpine

# Mercedes (standalone)
python scripts/extract_mercedes_dealers.py

# Other brands
python scripts/extract_other_brands_dealers.py honda
python scripts/extract_other_brands_dealers.py tesla polestar porsche
```

---

## Output Structure

```
Netherlands_Extract/
├── scripts/
│   ├── run_all.py                       # Master runner (all 26 brands)
│   ├── extract_stellantis_dealers.py    # 8 Stellantis brands
│   ├── extract_vwgroup_dealers.py       # 3 VW Group brands
│   ├── extract_renault_group_dealers.py # 2 Renault Group brands
│   ├── extract_mercedes_dealers.py      # Mercedes
│   └── extract_other_brands_dealers.py  # 12 independent brands
├── output/
│   ├── alfa_romeo/
│   │   ├── alfa_romeo_dealers_nl_YYYYMMDD_HHMMSS.csv
│   │   └── alfa_romeo_dealers_nl_YYYYMMDD_HHMMSS.json
│   ├── audi/
│   ├── citroen/
│   ├── ... (one folder per brand)
│   └── mercedes/
├── requirements.txt
└── README.md
```

---

## Data Fields Extracted

All records include:

| Field | Description |
|-------|-------------|
| `dealer_id` | Unique dealer identifier |
| `brand` | Brand name |
| `name` | Dealer/outlet name |
| `latitude` | GPS latitude |
| `longitude` | GPS longitude |
| `full_address` | Combined address string |
| `address_line_1` | Street address |
| `address_line_2` | Additional address info |
| `postal_code` | Dutch postal code |
| `city` | City |
| `country_code` | Always `NL` |
| `phone` | Contact phone |
| `email` | Contact email |
| `website` | Dealer website URL |
| `products` | Services/products offered |
| `products_count` | Number of products |

---

## API Platforms Used

| Platform | Brands | Method |
|----------|--------|--------|
| Stellantis DealersServlet | Alfa Romeo, Citroën, DS, Fiat, Jeep, Lancia, Opel, Peugeot | GET with geo + service filter |
| VW Group PSS GraphQL | Audi, CUPRA, SEAT | POST GraphQL with `activities: ["SALES"]` |
| Renault Group API | Alpine, Dacia | GET with geo coordinates |
| Mercedes DMS Plus | Mercedes | GET with location ID, multi-city search |
| Brand-specific REST | Honda, Land Rover, Lexus, Mazda, Mitsubishi, Nissan, Polestar, Porsche, Smart, Suzuki, Tesla, Mini | GET/POST per-brand |

---

## Notes

- All scripts filter for **SALES ONLY** (not service/parts-only sites)
- Multi-city search strategy ensures full Netherlands coverage
- Automatic deduplication by dealer ID
- Rate limiting with delays between requests
- Output in both **CSV** and **JSON** formats with timestamps
- If an API returns 0 results for a brand, the endpoint likely needs re-investigation (brands may change their APIs)

---

**Status (2026-03-23)**:
- **Stellantis**: ✅ Working (8/8 brands)
- **Mercedes**: 🔄 In Progress (Active, rate-limited)
- **VW Group**: ⚠️ Issue (403/0 results)
- **Renault**: ❌ Failed (DNS issue)
- **Other**: ✅ Complete (All 12 brands extracted)
