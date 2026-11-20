import re
import pycountry

#There is an issue with multiple cities, the function fails

CITY_TO_SUBDIVISION = {
    "new york city": "US-NY",
    "new york": "US-NY",
    "nyc": "US-NY",
    "washington dc": "US-DC",
    "washington d.c.": "US-DC",
    "washington": "US-DC",
    "toronto": "CA-ON",
    "ontario": "CA-ON",
    "edmonton": "CA-AB",
    "philadelphia": "US-PA",
    "pennsylvania": "US-PA",
    "montreal": "CA-QC",
    "quebec": "CA-QC",
    "vancouver": "CA-BC",
    "victoria": "CA-BC",
    "calgary": "CA-AB",
    "ottawa": "CA-ON",
    "los angeles": "US-CA",
    "chicago": "US-IL",
    "miami": "US-FL",
    "phily": "US-PA",
    "bangalore": "IN-KA",
    "bengaluru": "IN-KA",
    "chennai": "IN-TN",
    "hyderabad": "IN-TG",
    "delhi": "IN-DL",
    "mumbai": "IN-MH",
    "pune": "IN-MH",
}

def _clean_text(value):
    return re.sub(r"\s+", " ", (value or "")).strip()

def _split_city_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        items = value
    else:
        items = re.split(r"[,;]|\band\b|/", str(value))
    out = []
    for item in items:
        cleaned = _clean_text(item)
        if cleaned:
            out.append(cleaned)
    return out

def normalize_city_to_region_country(city):
    city = _clean_text(city)
    if not city:
        return None, None

    key = city.lower()
    if key in CITY_TO_SUBDIVISION:
        region_code = CITY_TO_SUBDIVISION[key]
        return region_code.split("-")[0], region_code

    for subdivision in pycountry.subdivisions:
        if city.lower() in {subdivision.name.lower(), subdivision.code.lower()}:
            return subdivision.country_code, subdivision.code

    return None, None

def normalize_location(city):
    country_code = None
    region_code = None

    for city_name in _split_city_list(city):
        city_country, city_region = normalize_city_to_region_country(city_name)
        if city_country and city_region:
            country_code = city_country
            region_code = city_region

    if country_code and region_code:
        return country_code, region_code, city

    #If it is not able to return any region or country, default city will be toronto
    print("Could not find country or region code, defaulting to Toronto, ON, Canada")
    city = "toronto"

    return "CA", "CA-ON", city