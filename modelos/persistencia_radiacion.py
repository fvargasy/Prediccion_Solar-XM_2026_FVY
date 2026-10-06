"""Línea base #2 (física): el perfil del último día, escalado por la radiación pronosticada.

gen_mañana(h) ≈ gen_ayer(h) · rad_mañana(día) / rad_ayer(día)
"""
import numpy as np

NOMBRE = "Persistencia × radiación"
AUTOR = "profe"


def predecir(historia, clima_dia):
    dia = historia.fecha_hora.dt.date.max()
    ultimo = historia[historia.fecha_hora.dt.date == dia].sort_values("fecha_hora")
    rad_ayer = ultimo["radiacion"].sum()
    rad_man = clima_dia["radiacion"].sum()
    factor = np.clip(rad_man / rad_ayer, 0.3, 2.0) if rad_ayer > 0 else 1.0
    return ultimo["solar_mwh"].to_numpy() * factor
