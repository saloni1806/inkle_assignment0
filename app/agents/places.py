import os
from dotenv import load_dotenv
import httpx
from typing import List
from ..models import PlaceInfo

load_dotenv()
OVERPASS_URL = "https://overpass-api.de/api/interpreter"
USER_AGENT = os.getenv("USER_AGENT", "inkle-ai-intern/1.0 (contact: chaurasiya.saloni18@gmail.com)")
HEADERS = {"User-Agent": USER_AGENT, "Accept-Language": "en"}

async def get_places(lat: float, lon: float, radius: int = 5000, limit: int = 5) -> List[PlaceInfo]:
    """
    Query Overpass API for nearby tourist/historic/leisure POIs.
    Returns up to `limit` PlaceInfo objects.
    """
    query = f"""
    [out:json][timeout:25];
    (
      node(around:{radius},{lat},{lon})["tourism"~"attraction|museum|viewpoint|zoo|theme_park|gallery"];
      way(around:{radius},{lat},{lon})["tourism"~"attraction|museum|viewpoint|zoo|theme_park|gallery"];
      relation(around:{radius},{lat},{lon})["tourism"~"attraction|museum|viewpoint|zoo|theme_park|gallery"];
      node(around:{radius},{lat},{lon})["historic"];
      way(around:{radius},{lat},{lon})["historic"];
      relation(around:{radius},{lat},{lon})["historic"];
      node(around:{radius},{lat},{lon})["leisure"~"park|garden"];
      way(around:{radius},{lat},{lon})["leisure"~"park|garden"];
    );
    out center 50;
    """

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # pass headers explicitly to ensure User-Agent is sent
            response = await client.post(OVERPASS_URL, data={"data": query}, headers=HEADERS)
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPStatusError as e:
        # return empty list or raise a descriptive error depending on your design choice
        raise Exception(f"Overpass API error {e.response.status_code} for url {e.request.url}") 
    except Exception as e:
        raise

    elements = data.get("elements", [])
    places: List[PlaceInfo] = []
    seen = set()
    for el in elements:
        tags = el.get("tags", {}) or {}
        name = tags.get("name")
        if not name:
            continue
        if name in seen:
            continue
        seen.add(name)

        ptype = tags.get("tourism") or tags.get("historic") or tags.get("leisure")
        lat_el = el.get("lat") or (el.get("center", {}).get("lat") if el.get("center") else None)
        lon_el = el.get("lon") or (el.get("center", {}).get("lon") if el.get("center") else None)

        places.append(PlaceInfo(name=name, type=ptype, lat=lat_el, lon=lon_el))
        if len(places) >= limit:
            break

    return places
