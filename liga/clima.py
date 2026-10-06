"""Clima horario desde Open-Meteo (gratis, sin API key).

Promediamos varios 'núcleos solares' de Colombia donde está concentrada la capacidad instalada.
Con past_days=92 obtenemos el pasado reciente + el pronóstico de los próximos días en una sola consulta.
"""
from __future__ import annotations

import pandas as pd
import requests

# Puntos aproximados de los principales clústeres de parques solares
NUCLEOS = {
    "Cesar (El Paso / Valledupar)": (9.95, -73.55),
    "Atlántico-Bolívar (Guayepo)": (10.40, -75.03),
    "Tolima (Espinal / Ambalema)": (4.15, -74.88),
    "Córdoba-Sucre": (8.75, -75.60),
}
VARIABLES = ["shortwave_radiation", "cloud_cover", "temperature_2m"]
RENOMBRE = {"shortwave_radiation": "radiacion", "cloud_cover": "nubosidad",
            "temperature_2m": "temperatura"}


def clima_nucleos(past_days: int = 92, forecast_days: int = 3) -> pd.DataFrame:
    tablas = []
    for nombre, (lat, lon) in NUCLEOS.items():
        r = requests.get("https://api.open-meteo.com/v1/forecast", timeout=60, params={
            "latitude": lat, "longitude": lon, "hourly": ",".join(VARIABLES),
            "timezone": "America/Bogota", "past_days": past_days, "forecast_days": forecast_days})
        r.raise_for_status()
        h = pd.DataFrame(r.json()["hourly"])
        h["fecha_hora"] = pd.to_datetime(h.pop("time"))
        tablas.append(h)
    df = pd.concat(tablas).groupby("fecha_hora", as_index=False).mean(numeric_only=True)
    return df.rename(columns=RENOMBRE)
