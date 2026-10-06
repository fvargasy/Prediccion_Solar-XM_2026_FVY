"""Construye y cachea el dataset horario: generación solar XM + clima Open-Meteo.

datos/historico.csv  -> fecha_hora, solar_mwh, radiacion, nubosidad, temperatura
datos/clima.csv      -> clima reciente + pronóstico (incluye los días que vienen)
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
DATOS = RAIZ / "datos"
HIST = DATOS / "historico.csv"
CLIMA = DATOS / "clima.csv"
DIAS_HISTORIA = 90


def actualizar(demo: bool = False) -> tuple[pd.DataFrame, pd.DataFrame]:
    DATOS.mkdir(exist_ok=True)
    if demo:
        gen, clima = datos_sinteticos()
    else:
        from . import clima as cl, xm
        hoy = dt.date.today()
        inicio = hoy - dt.timedelta(days=DIAS_HISTORIA)
        print("Descargando generación solar de XM…")
        gen = xm.generacion_solar_nacional(inicio, hoy)
        print("Descargando clima de Open-Meteo…")
        clima = cl.clima_nucleos()
        # Mezclamos con el caché para no perder historia
        if HIST.exists():
            viejo = pd.read_csv(HIST, parse_dates=["fecha_hora"])[["fecha_hora", "solar_mwh"]]
            gen = pd.concat([viejo, gen]).drop_duplicates("fecha_hora", keep="last")
    gen = _dias_completos(gen)
    hist = gen.merge(clima, on="fecha_hora", how="left").sort_values("fecha_hora")
    hist.to_csv(HIST, index=False)
    clima.to_csv(CLIMA, index=False)
    print(f"Histórico: {hist.fecha_hora.min():%Y-%m-%d} → {hist.fecha_hora.max():%Y-%m-%d} "
          f"({hist.fecha_hora.dt.date.nunique()} días)")
    return hist, clima


def cargar() -> tuple[pd.DataFrame, pd.DataFrame]:
    return (pd.read_csv(HIST, parse_dates=["fecha_hora"]),
            pd.read_csv(CLIMA, parse_dates=["fecha_hora"]))


def _dias_completos(gen: pd.DataFrame) -> pd.DataFrame:
    """XM publica con rezago; descartamos días con horas faltantes o en cero total."""
    g = gen.dropna(subset=["solar_mwh"]).copy()
    g["fecha"] = g.fecha_hora.dt.date
    stats = g.groupby("fecha")["solar_mwh"].agg(["count", "sum"])
    ok = stats[(stats["count"] == 24) & (stats["sum"] > 0)].index
    return g[g.fecha.isin(ok)].drop(columns="fecha").reset_index(drop=True)


def datos_sinteticos(dias: int = DIAS_HISTORIA, semilla: int = 7):
    """Datos realistas de juguete para probar sin internet (modo --demo)."""
    rng = np.random.default_rng(semilla)
    hoy = pd.Timestamp(dt.date.today())
    horas = pd.date_range(hoy - pd.Timedelta(days=dias), hoy + pd.Timedelta(days=3),
                          freq="h", inclusive="left")
    h = horas.hour.values
    doy = horas.dayofyear.values
    cielo = np.clip(np.sin(np.pi * (h - 6) / 12), 0, None) * (1000 + 60 * np.sin(2 * np.pi * doy / 365))
    nub_dia = np.repeat(rng.beta(2, 3, len(horas) // 24 + 1) * 100, 24)[: len(horas)]
    nub = np.clip(nub_dia + rng.normal(0, 12, len(horas)), 0, 100)
    rad = cielo * (1 - 0.7 * nub / 100)
    temp = 24 + 7 * np.clip(np.sin(np.pi * (h - 7) / 14), -0.3, None) - 0.04 * nub
    cap = np.linspace(1400, 1600, len(horas))  # MW instalados creciendo
    solar = cap * rad / 1000 * (1 - 0.004 * (temp - 25)) * 0.8 + rng.normal(0, 15, len(horas))
    solar = np.clip(np.where(rad < 5, 0, solar), 0, None)
    clima = pd.DataFrame({"fecha_hora": horas, "radiacion": rad, "nubosidad": nub, "temperatura": temp})
    ultimo_xm = hoy - pd.Timedelta(days=1)  # simulamos el rezago de publicación de XM
    gen = pd.DataFrame({"fecha_hora": horas, "solar_mwh": solar})
    gen = gen[gen.fecha_hora < ultimo_xm]
    return gen, clima
