from fastapi import FastAPI, HTTPException
from .models import PlanRequest
from .agents.geocode import geocode
from .agents.weather import get_weather
from .agents.places import get_places
import asyncio

app = FastAPI(title="Inkle Multi-Agent Tourism System")

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/plan")
async def plan(req: PlanRequest):
    place = req.place.strip()
    tasks = req.tasks or ["weather", "places"]

    # -----------------------------------------
    # GEOCODE CHILD AGENT (with safe error JSON)
    # -----------------------------------------
    try:
        geo = await geocode(place)
    except Exception as e:
        return {
            "ok": False,
            "error": f"Geocoding service error: {str(e)}"
        }

    # If place not found
    if not geo:
        return {
            "ok": False,
            "error": f"I don't know this place exists: {place}"
        }

    lat = geo["lat"]
    lon = geo["lon"]

    # ----------------------------------------------------
    # RUN CHILD AGENTS (weather + places) CONCURRENTLY
    # ----------------------------------------------------
    coros = {}
    if "weather" in tasks:
        coros["weather"] = get_weather(lat, lon)
    if "places" in tasks:
        coros["places"] = get_places(lat, lon)

    results = {}
    if coros:
        completed = await asyncio.gather(
            *coros.values(),
            return_exceptions=True
        )
        for key, res in zip(coros.keys(), completed):
            if isinstance(res, Exception):
                results[key] = {"error": str(res)}
            else:
                results[key] = res

    # ----------------------------------------------------
    # FORMAT FRIENDLY TEXT RESPONSE
    # ----------------------------------------------------
    parts = []

    # Weather
    if "weather" in results and isinstance(results["weather"], dict):
        w = results["weather"]
        temp = w.get("temperature_c")
        prob = w.get("precipitation_probability_percent")

        if temp is not None:
            text = f"In {place} it's currently {temp}°C"
            if prob is not None:
                text += f" with a chance of {prob}% to rain."
            else:
                text += "."
            parts.append(text)

    # Places
    if "places" in results and isinstance(results["places"], list):
        places_list = results["places"]
        if places_list:
            names = "\n".join([f"- {p.name}" for p in places_list])
            parts.append(f"And these are the places you can go:\n{names}")
        else:
            parts.append("I couldn't find tourist places nearby.")

    final_text = " ".join(parts) if parts else "No tasks requested."

    # ----------------------------------------------------
    # FINAL JSON OUTPUT
    # ----------------------------------------------------
    return {
        "ok": True,
        "place": place,
        "coords": {"lat": lat, "lon": lon},
        "text": final_text,
        "raw": results
    }
