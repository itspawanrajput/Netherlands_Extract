---
name: car_dealer_extraction
description: "A skill for extracting and normalizing car dealer data (Sales/Service) from brand-specific web APIs across different markets."
---

# Car Dealer Extraction Skill

This skill documents the systematic process of identifying, capturing, and transforming car dealer data from various automotive brand websites into a standardized format.

## Objectives
- Identify the correct API endpoints for car dealer locators.
- Capture the request structure (Headers, Cookies, Payload).
- Standardize varying JSON responses into a unified CSV/JSON schema.
- Filter for specific services (e.g., "Sales Only").

## Standard Schema (Netherlands Example)
All extractions should attempt to populate these fields:
- `dealer_id`: Unique identifier from the brand API.
- `brand`: Brand name (e.g., "Tesla", "Honda").
- `name`: Full dealership name.
- `latitude` / `longitude`: Geocoordinates.
- `full_address`: Combined street, house number, zip, and city.
- `address_line_1`: Street name and house number.
- `address_line_2`: Optional (Building name, floor, etc.).
- `postal_code`: Zip code.
- `city`: City name.
- `country_code`: 2-letter ISO code (e.g., "NL").
- `phone`: Primary contact number (Sales preferably).
- `email`: Primary contact email.
- `website`: Dealer's specific landing page or homepage.
- `products`: List of services (e.g., "Sales", "Service", "Parts").
- `products_count`: Number of available services.

## Workflow

### 1. Endpoint Discovery
- Open the brand's "Find a Dealer" page in a browser.
- Use Network Tab (XHR/Fetch) to find requests containing dealer lists.
- **Tip**: Look for keywords like `dealers`, `pois`, `locations`, `outlets`, `search`.

### 2. cURL Analysis
- Copy the request as **cURL (bash)**.
- Identify critical headers: `User-Agent`, `Referer`, `x-api-key`, `Authorization`.
- Check if cookies are mandatory (e.g., `OptanonConsent`).

### 3. Implementation Patterns

#### Geo-Iterative Extraction
If the API only returns dealers within a certain radius:
- Use a pre-defined list of major cities/coordinates for the target country.
- Loop through coordinates and collect results.
- Implement a **Seen Set** to avoid duplicates by `dealer_id`.

#### Single-Query Extraction
If the API supports country-level queries:
- Set `radius` to a very high value (e.g., `1000km`) or `marketId` to the country code.
- Increase `pageSize` or `limit` to capture all results in one go.

### 4. Normalization
Since every brand uses a different JSON structure:
- Use local normalization within the extraction function.
- Create helper functions (e.g., `_normalise_jlr`) for brands sharing a platform.

### 5. Filtering
- Always look for flags like `is_sales_dealer`, `facilityType: PORSCHE_CENTER`, or service names in a list.
- Ensure only dealers providing the requested "Product" (e.g., New Car Sales) are included.

## Handling Common Issues
- **403 Forbidden**: Likely missing headers (Referer/User-Agent) or blocked by WAF (e.g., Akamai/Vercel).
- **DNS Failures**: API endpoint might be internal or deprecated.
- **Empty Results**: Check if coordinates are in the correct format (Lat/Lng vs Lng/Lat) or if the radius is too small.

## Tools & Libraries
- `requests`: Main library for API calls.
- `beautifulsoup4`: For parsing HTML if data is embedded in a script tag (e.g., `window.__remixContext`).
- `json`: Parsing responses.
- `csv`: Saving results.
