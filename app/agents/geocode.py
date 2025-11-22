# app/agents/geocode.py
import os
import json
import asyncio
from typing import Optional, Dict
from dotenv import load_dotenv
import httpx

load_dotenv()

# Config
CACHE_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "geocode_cache.json")
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
LOCATIONIQ_URL = "https://us1.locationiq.com/v1/search.php"
USER_AGENT = os.getenv("USER_AGENT", "inkle-tourism/1.0 (contact: chaurasiya.saloni18@gmail.com)")
LOCATIONIQ_KEY = os.getenv("LOCATIONIQ_KEY")  # optional

HEADERS = {"User-Agent": USER_AGENT, "Accept-Language": "en"}

# Simple persistent JSON cache
def _read_cache() -> Dict[str, Dict]:
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def _write_cache(cache: Dict[str, Dict]):
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

async def _call_url(url: str, params: dict, headers: dict, timeout: float = 20.0):
    async with httpx.AsyncClient(timeout=timeout) as client:
        r = await client.get(url, params=params, headers=headers)
        r.raise_for_status()
        return r.json()

async def _try_nominatim(place: str):
    params = {"q": place, "format": "json", "limit": 1}
    data = await _call_url(NOMINATIM_URL, params, HEADERS)
    if not data:
        return None
    first = data[0]
    return {"lat": float(first["lat"]), "lon": float(first["lon"]), "display_name": first.get("display_name")}

async def _try_locationiq(place: str):
    if not LOCATIONIQ_KEY:
        return None
    params = {"key": LOCATIONIQ_KEY, "q": place, "format": "json", "limit": 1}
    data = await _call_url(LOCATIONIQ_URL, params, HEADERS)
    if not data:
        return None
    first = data[0]
    return {"lat": float(first["lat"]), "lon": float(first["lon"]), "display_name": first.get("display_name")}

async def geocode(place: str, max_retries: int = 3) -> Optional[Dict]:
    """
    Geocode with:
      1) persistent on-disk cache
      2) Nominatim with retries/backoff
      3) optional LocationIQ fallback (if LOCATIONIQ_KEY set)
    """
    place_key = place.strip().lower()
    cache = _read_cache()
    if place_key in cache:
        return cache[place_key]

    delay = 1.0
    for attempt in range(1, max_retries + 1):
        try:
            # primary: Nominatim
            res = await _try_nominatim(place)
            if res:
                cache[place_key] = res
                _write_cache(cache)
                return res
            # Nominatim returned empty: do not retry for empties; return None
            return None
        except httpx.HTTPStatusError as e:
            status = e.response.status_code
            # on 403/429 we wait and retry (transient limits)
            if status in (403, 429) and attempt < max_retries:
                await asyncio.sleep(delay)
                delay *= 2
                continue
            # for other HTTP errors, try fallback if available
            if LOCATIONIQ_KEY:
                try:
                    res = await _try_locationiq(place)
                    if res:
                        cache[place_key] = res
                        _write_cache(cache)
                        return res
                except Exception:
                    pass
            raise Exception(f"Client error {status} for url {e.request.url!s}")
        except (httpx.ConnectError, httpx.ReadTimeout) as e:
            if attempt < max_retries:
                await asyncio.sleep(delay)
                delay *= 2
                continue
            raise Exception(f"Network error: {str(e)}")
        except Exception:
            raise

    # final fallback: try LocationIQ once if key present
    if LOCATIONIQ_KEY:
        res = await _try_locationiq(place)
        if res:
            cache[place_key] = res
            _write_cache(cache)
            return res

    return None
