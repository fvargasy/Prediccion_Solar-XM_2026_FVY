"""SolarNet-GRU: red recurrente bidireccional que se re-entrena cada día (online learning).

Idea: para predecir el día D, la red 'lee' las 24 horas en secuencia. En cada hora h ve:
  - la generación del último día conocido a esa hora (memoria del sistema),
  - el pronóstico de radiación, nubosidad y temperatura para D a esa hora,
  - la hora codificada con seno/coseno.
y devuelve la generación de D hora a hora. La GRU bidireccional permite que la mañana 'sepa'
cómo será la tarde (p. ej. un frente nuboso), algo que un modelo por hora no ve.

Entrena en segundos en CPU (≈90 días de datos), así que corre dentro de GitHub Actions.
"""
import numpy as np
import pandas as pd
import torch
from torch import nn

NOMBRE = "SolarNet-GRU"
AUTOR = "profe"
EPOCAS = 400
SEMILLA = 42


class SolarNet(nn.Module):
    def __init__(self, n_in=6, oculto=32):
        super().__init__()
        self.gru = nn.GRU(n_in, oculto, batch_first=True, bidirectional=True)
        self.cabeza = nn.Sequential(nn.Linear(2 * oculto, 16), nn.ReLU(), nn.Linear(16, 1))

    def forward(self, x):                  # x: (lote, 24, n_in)
        z, _ = self.gru(x)
        return torch.relu(self.cabeza(z)).squeeze(-1)   # generación ≥ 0


def _features(gen_ref, clima_dia, escala):
    h = np.arange(24)
    return np.column_stack([
        gen_ref / escala,
        clima_dia["radiacion"].to_numpy() / 1000,
        clima_dia["nubosidad"].to_numpy() / 100,
        (clima_dia["temperatura"].to_numpy() - 25) / 10,
        np.sin(2 * np.pi * h / 24), np.cos(2 * np.pi * h / 24),
    ]).astype(np.float32)


def _por_dia(df):
    return {d: g.sort_values("fecha_hora") for d, g in df.groupby(df.fecha_hora.dt.date) if len(g) == 24}


def predecir(historia, clima_dia):
    torch.manual_seed(SEMILLA)
    np.random.seed(SEMILLA)
    dias = _por_dia(historia)
    fechas = sorted(dias)
    objetivo = pd.Timestamp(clima_dia.fecha_hora.iloc[0]).date()
    rezago = (objetivo - fechas[-1]).days          # entrenamos con el mismo rezago que XM
    escala = max(historia["solar_mwh"].max(), 1.0)

    X, Y = [], []
    for d in fechas:
        ref = d - pd.Timedelta(days=rezago).to_pytimedelta()
        if ref in dias and dias[d]["radiacion"].notna().all():
            X.append(_features(dias[ref]["solar_mwh"].to_numpy(), dias[d], escala))
            Y.append(dias[d]["solar_mwh"].to_numpy() / escala)
    X, Y = torch.tensor(np.array(X)), torch.tensor(np.array(Y), dtype=torch.float32)

    red = SolarNet()
    opt = torch.optim.AdamW(red.parameters(), lr=5e-3, weight_decay=1e-4)
    for _ in range(EPOCAS):
        opt.zero_grad()
        perdida = nn.functional.mse_loss(red(X), Y)
        perdida.backward()
        opt.step()

    x = torch.tensor(_features(dias[fechas[-1]]["solar_mwh"].to_numpy(), clima_dia, escala))[None]
    with torch.no_grad():
        return red(x)[0].numpy() * escala
