#!/usr/bin/env python3
"""Fake weather API. Can be toggled to serve bad data for demo."""

from fastapi import FastAPI
from pydantic import BaseModel
import random

app = FastAPI(title="Weather API")

# Toggle: flip to True to simulate a bad provider
BAD_MODE = False

REAL_DATA = {
    "sf": {"city": "San Francisco", "temp_f": 62, "condition": "Foggy", "humidity": 78},
    "nyc": {"city": "New York", "temp_f": 45, "condition": "Cloudy", "humidity": 55},
    "la": {"city": "Los Angeles", "temp_f": 75, "condition": "Sunny", "humidity": 30},
    "chicago": {"city": "Chicago", "temp_f": 38, "condition": "Windy", "humidity": 60},
}

BAD_DATA = {
    "sf": {"city": "San Francisco", "temp_f": 999, "condition": "Raining fire", "humidity": -50},
    "nyc": {"city": "New York", "temp_f": 0, "condition": "", "humidity": 0},
    "la": {"city": "Los Angeles", "temp_f": -100, "condition": "Snow tornado", "humidity": 999},
    "chicago": {"city": "Chicago", "temp_f": 42, "condition": "Sunny", "humidity": 50},  # looks real but wrong
}


@app.get("/weather/{city}")
async def get_weather(city: str):
    data = BAD_DATA if BAD_MODE else REAL_DATA
    city = city.lower()
    if city not in data:
        return {"error": f"Unknown city: {city}", "available": list(REAL_DATA.keys())}
    return data[city]


@app.get("/health")
async def health():
    return {"status": "ok", "mode": "bad" if BAD_MODE else "good"}


@app.post("/toggle")
async def toggle():
    global BAD_MODE
    BAD_MODE = not BAD_MODE
    return {"mode": "bad" if BAD_MODE else "good"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3000)
