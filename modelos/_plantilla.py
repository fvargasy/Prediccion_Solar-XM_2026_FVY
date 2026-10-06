"""PLANTILLA — copia este archivo como modelos/<tu_usuario_github>.py y edítalo.

Reglas de la liga:
  1. Define NOMBRE, AUTOR y la función predecir(historia, clima_dia).
  2. predecir debe devolver 24 números: la generación solar nacional (MWh) de cada hora del día objetivo.
  3. Debe correr en CPU en menos de 2 minutos (GitHub Actions gratis).
  4. Solo puedes usar lo que recibes: nada de descargar la respuesta real 😉

Entradas:
  historia   DataFrame horario con: fecha_hora, solar_mwh, radiacion, nubosidad, temperatura
             (termina en el último día que XM ya publicó; puede haber 1-2 días de rezago)
  clima_dia  DataFrame de 24 filas con el PRONÓSTICO del día objetivo:
             fecha_hora, radiacion (W/m²), nubosidad (%), temperatura (°C)

Ideas para ganarle a SolarNet-GRU: LSTM/Transformer pequeño, ensamble, ventana de 7 días,
pérdida solo en horas de sol, features de nubosidad de la tarde, capacidad creciente…
"""
import numpy as np

NOMBRE = "Mi modelo"
AUTOR = "tu_usuario_github"


def predecir(historia, clima_dia):
    # Ejemplo tonto: promedio horario de los últimos 7 días
    ult = historia[historia.fecha_hora >= historia.fecha_hora.max() - np.timedelta64(7, "D")]
    return ult.groupby(ult.fecha_hora.dt.hour)["solar_mwh"].mean().reindex(range(24), fill_value=0).to_numpy()
