# Netherlands Extract Task Status - 2026-03-23

Summary of the current state of data extraction for **26 car brands** in the Netherlands (SALES ONLY).

## Extraction Progress

| Group | Brands | Status | Notes |
|-------|--------|--------|-------|
| **Stellantis** | Alfa Romeo, Citroen, DS, Fiat, Jeep, Lancia, Opel, Peugeot | ✅ Complete | All 8 brands successfully extracted (approx. 240 records). |
| **VW Group** | Audi, CUPRA, SEAT | ⚠️ Issue | Audi (0), CUPRA/SEAT (403 Forbidden). API likely blocking or headers outdated. |
| **Renault Group**| Alpine, Dacia | ❌ Failed | DNS resolution failed for `api-dl.renault.com`. Endpoint needs update. |
| **Mercedes** | Mercedes | 🔄 In Progress | Running for ~20 mins. API is likely rate-limiting (60s delays observed in script logic). |
| **Other** | Honda, JLR, Lexus, Mazda, Mitsubishi, Nissan, Polestar, Porsche, Smart, Suzuki, Tesla, Mini (12 total) | ⏳ Pending | To be run by [extract_other_brands_dealers.py](file:///Users/itspawanrajput/Desktop/Netherlands_Extract/scripts/extract_other_brands_dealers.py) next. |

## Key Technical Findings

- **Stellantis**: Confirmed working perfectly as of 2026-03-23.
- **VW Group**: The PSS GraphQL API (`graphql.pss.audi.com`) requires investigation. Headers or `clientid` may be outdated.
- **Renault Group**: The host `api-dl.renault.com` is unreachable. Needs updated endpoint discovery.
- **Mercedes**: The DMS Plus API is active but strictly rate-limited. Script incorporates automatic retry and wait logic (60s pauses).

## Running Summary
Currently running master script using `uv` for dependency management.
- **Process ID**: 8576 (Master), 9036 (Mercedes child)
- **Start Time**: 16:42:36 (Current: 17:11:00)
- **Expected Completion**: TBD (approx. 40-60 mins total due to rate limiting).

## Next Steps
1. Finish running the remaining **12 "Other" brands**.
2. Debug **VW Group** 403/0 result issues.
3. Find new API endpoint for **Renault/Dacia**.
