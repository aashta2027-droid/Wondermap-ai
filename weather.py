import requests
import streamlit as st

AREAS = {
    "Port Blair": (11.62, 92.73),
    "Wandoor": (11.58, 92.61),
    "Chidiya Tapu": (11.50, 92.71),
    "Havelock Island": (11.97, 92.98),
    "Neil Island": (11.83, 93.04),
    "Baratang": (12.08, 92.76),
    "Long Island": (12.37, 92.93),
    "Rangat": (12.50, 92.92),
    "Mayabunder": (12.92, 92.90),
    "Diglipur": (13.25, 92.97),
    "Little Andaman": (10.58, 92.55),
}


def describe(code):
    try:
        c = int(code)
    except Exception:
        return ("Unknown", "")
    if c == 0:
        return ("Clear sky", "☀️")
    if c in (1, 2):
        return ("Partly cloudy", "⛅")
    if c == 3:
        return ("Overcast", "☁️")
    if c in (45, 48):
        return ("Fog", "🌫️")
    if 51 <= c <= 57:
        return ("Drizzle", "🌦️")
    if 61 <= c <= 67:
        return ("Rain", "🌧️")
    if 80 <= c <= 82:
        return ("Rain showers", "🌦️")
    if c >= 95:
        return ("Thunderstorm", "⛈️")
    return ("Mixed weather", "🌥️")


@st.cache_data(ttl=900, show_spinner=False)
def get_weather(lat, lng):
    r = requests.get("https://api.open-meteo.com/v1/forecast", params={
        "latitude": lat, "longitude": lng,
        "current": "temperature_2m,apparent_temperature,relative_humidity_2m,precipitation,weather_code,wind_speed_10m",
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max",
        "forecast_days": 3, "timezone": "Asia/Kolkata"}, timeout=8)
    r.raise_for_status()
    data = r.json()
    cur = data["current"]
    daily = data["daily"]
    days = []
    for i, d in enumerate(daily["time"]):
        days.append({"date": d, "code": daily["weather_code"][i],
                     "max": daily["temperature_2m_max"][i], "min": daily["temperature_2m_min"][i],
                     "rain": daily["precipitation_probability_max"][i]})
    wave = None
    try:
        m = requests.get("https://marine-api.open-meteo.com/v1/marine", params={
            "latitude": lat, "longitude": lng, "current": "wave_height",
            "timezone": "Asia/Kolkata"}, timeout=6)
        if m.status_code == 200:
            wave = (m.json().get("current") or {}).get("wave_height")
    except Exception:
        wave = None
    return {"now": cur, "days": days, "wave": wave}
# END OF FILE
