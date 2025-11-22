
import httpx

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

async def get_weather(lat: float, lon: float):
    params = {
        "latitude": lat,
        "longitude": lon,
        "current_weather": True,
        "hourly": "precipitation_probability",
        "timezone": "UTC"
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        r = await client.get(OPEN_METEO_URL, params=params)
        r.raise_for_status()
        data = r.json()

    temp = data.get("current_weather", {}).get("temperature")
    hourly = data.get("hourly", {}).get("precipitation_probability", [])
    rain = max(hourly[:24]) if hourly else None

    return {
        "temperature_c": temp,
        "precipitation_probability_percent": rain,
        "raw": data
    }
