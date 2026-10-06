"""Corre la liga completa: datos → predicciones de todos los modelos → calificación → leaderboard.

Uso:
  python -m liga.run_diario                  # modo real (API XM + Open-Meteo)
  python -m liga.run_diario --demo           # datos sintéticos, sin internet
  python -m liga.run_diario --backtest 14    # además re-evalúa los últimos 14 días (arranque en frío)
"""
from __future__ import annotations

import argparse
import datetime as dt
import importlib.util
import time
from pathlib import Path
from zoneinfo import ZoneInfo

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from . import datos  # noqa: E402

RAIZ = datos.RAIZ
PRED = RAIZ / "predicciones"
RES = RAIZ / "resultados"
HORAS_SOL = list(range(6, 19))
BASE = "Persistencia"


# ---------------------------------------------------------------- modelos
def cargar_modelos() -> dict:
    modelos = {}
    for f in sorted((RAIZ / "modelos").glob("*.py")):
        if f.name.startswith("_"):
            continue
        spec = importlib.util.spec_from_file_location(f.stem, f)
        mod = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(mod)
            modelos[getattr(mod, "NOMBRE", f.stem)] = mod
        except Exception as e:  # noqa: BLE001
            print(f"  ⚠ {f.name} no carga: {e}")
    return modelos


def correr(modelos: dict, historia: pd.DataFrame, clima_dia: pd.DataFrame) -> dict:
    salida = {}
    for nombre, mod in modelos.items():
        t0 = time.time()
        try:
            y = np.asarray(mod.predecir(historia.copy(), clima_dia.copy()), dtype=float).ravel()
            if y.shape != (24,) or not np.isfinite(y).all():
                raise ValueError(f"devolvió forma {y.shape} o valores no finitos")
            salida[nombre] = np.clip(y, 0, None)
            print(f"  ✓ {nombre:<28} {time.time() - t0:5.1f}s")
        except Exception as e:  # noqa: BLE001
            print(f"  ✗ {nombre:<28} falló: {e}")
    return salida


def clima_de(clima: pd.DataFrame, dia: dt.date) -> pd.DataFrame:
    c = clima[clima.fecha_hora.dt.date == dia].sort_values("fecha_hora").reset_index(drop=True)
    if len(c) != 24:
        raise RuntimeError(f"No hay pronóstico completo de clima para {dia}")
    return c


# ---------------------------------------------------------------- predicción del día
def predecir_manana(hist, clima, modelos):
    manana = dt.datetime.now(ZoneInfo("America/Bogota")).date() + dt.timedelta(days=1)
    print(f"\n▶ Pronóstico oficial para {manana} (último dato XM: {hist.fecha_hora.max():%Y-%m-%d})")
    archivo = PRED / f"{manana}.csv"
    previo = pd.read_csv(archivo) if archivo.exists() else pd.DataFrame({"hora": range(24)})
    # Regla anti-trampa: la primera predicción emitida para un día NO se sobreescribe
    faltan = {k: v for k, v in modelos.items() if k not in previo.columns}
    preds = correr(faltan, hist, clima_de(clima, manana))
    for k, v in preds.items():
        previo[k] = np.round(v, 2)
    PRED.mkdir(exist_ok=True)
    previo.to_csv(archivo, index=False)


def backtest(hist, clima, modelos, n: int):
    print(f"\n▶ Backtest de los últimos {n} días")
    fechas = sorted(hist.fecha_hora.dt.date.unique())[-n:]
    filas = []
    for d in fechas:
        h = hist[hist.fecha_hora.dt.date < d - dt.timedelta(days=1)]   # simula rezago de 2 días
        print(f" {d}")
        for k, v in correr(modelos, h, clima_de(clima, d)).items():
            filas += [{"fecha": d, "hora": i, "modelo": k, "pred": x} for i, x in enumerate(v)]
    pd.DataFrame(filas).to_csv(RES / "backtest.csv", index=False)


# ---------------------------------------------------------------- calificación
def _largo_oficial() -> pd.DataFrame:
    filas = []
    for f in sorted(PRED.glob("*.csv")):
        df = pd.read_csv(f).melt(id_vars="hora", var_name="modelo", value_name="pred")
        df["fecha"] = dt.date.fromisoformat(f.stem)
        filas.append(df)
    return pd.concat(filas) if filas else pd.DataFrame(columns=["fecha", "hora", "modelo", "pred"])


def calificar(hist: pd.DataFrame, largo: pd.DataFrame) -> pd.DataFrame:
    real = hist.assign(fecha=hist.fecha_hora.dt.date, hora=hist.fecha_hora.dt.hour)[["fecha", "hora", "solar_mwh"]]
    m = largo.assign(fecha=pd.to_datetime(largo.fecha).dt.date).merge(real, on=["fecha", "hora"])
    m = m[m.hora.isin(HORAS_SOL)]
    if m.empty:
        return pd.DataFrame()
    m["ae"] = (m.pred - m.solar_mwh).abs()
    dia = m.groupby(["modelo", "fecha"]).agg(mae=("ae", "mean"), media=("solar_mwh", "mean")).reset_index()
    base = dia[dia.modelo == BASE].set_index("fecha")["mae"]
    dia["skill"] = 1 - dia.mae / dia.fecha.map(base)
    tabla = dia.groupby("modelo").agg(dias=("fecha", "nunique"), mae_mwh=("mae", "mean"),
                                      skill=("skill", "mean"))
    tabla["nmae"] = dia.groupby("modelo").apply(lambda g: g.mae.sum() / g.media.sum(), include_groups=False)
    return tabla.sort_values("mae_mwh")


def _tabla_md(t: pd.DataFrame, autores: dict) -> str:
    if t.empty:
        return "_Aún no hay días calificados: XM publica con 1-2 días de rezago._\n"
    lin = ["| # | Modelo | Autor | Días | MAE (MWh) | nMAE | Skill vs persistencia |",
           "|---|---|---|---|---|---|---|"]
    medallas = ["🥇", "🥈", "🥉"]
    for i, (k, r) in enumerate(t.iterrows()):
        pos = medallas[i] if i < 3 else str(i + 1)
        sk = "—" if k == BASE or pd.isna(r.skill) else f"{r.skill:+.1%}"
        lin.append(f"| {pos} | {k} | {autores.get(k, '?')} | {int(r.dias)} | {r.mae_mwh:.1f} | {r.nmae:.1%} | {sk} |")
    return "\n".join(lin) + "\n"


def grafica(hist, largo, titulo, archivo):
    largo = largo.assign(fecha=pd.to_datetime(largo.fecha).dt.date)
    dias_ok = sorted(set(largo.fecha) & set(hist.fecha_hora.dt.date))
    if not dias_ok:
        return False
    d = dias_ok[-1]
    real = hist[hist.fecha_hora.dt.date == d].sort_values("fecha_hora")
    fig, ax = plt.subplots(figsize=(9, 4.2), dpi=120)
    ax.fill_between(range(24), real.solar_mwh, color="#E9C46A", alpha=.35, label="Real (XM)")
    ax.plot(range(24), real.solar_mwh.to_numpy(), color="#8A6D1F", lw=2)
    paleta = ["#C8553D", "#588B8B", "#6D597A", "#2A6F97", "#B56576", "#43AA8B"]
    for i, (k, g) in enumerate(largo[largo.fecha == d].groupby("modelo")):
        ax.plot(g.hora, g.pred, lw=1.6, ls="--" if k == BASE else "-", color=paleta[i % len(paleta)], label=k)
    ax.set(title=f"{titulo} — {d}", xlabel="Hora", ylabel="Generación solar SIN (MWh)", xlim=(4, 20))
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False, fontsize=8, ncol=2)
    fig.tight_layout()
    fig.savefig(archivo)
    plt.close(fig)
    return True


def leaderboard(hist, modelos):
    autores = {k: getattr(m, "AUTOR", "?") for k, m in modelos.items()}
    oficial = _largo_oficial()
    t_of = calificar(hist, oficial)
    bt_path = RES / "backtest.csv"
    bt = pd.read_csv(bt_path) if bt_path.exists() else pd.DataFrame()
    t_bt = calificar(hist, bt) if not bt.empty else pd.DataFrame()
    g1 = grafica(hist, oficial, "Pronóstico oficial vs real", RES / "ultimo_dia.png") if not oficial.empty else False
    g2 = grafica(hist, bt, "Backtest", RES / "backtest.png") if not bt.empty else False
    ahora = dt.datetime.now(ZoneInfo("America/Bogota")).strftime("%Y-%m-%d %H:%M")
    md = [f"# ☀️ Liga de Pronóstico Solar Colombia — Leaderboard\n",
          f"_Actualizado: {ahora} (hora Colombia) · Métrica: MAE en horas de sol (06–18 h) · "
          f"Skill = 1 − MAE/MAE_persistencia (positivo = le ganas a la persistencia)_\n",
          "## 🏆 Liga oficial (predicciones hechas ANTES de conocer el dato real)\n", _tabla_md(t_of, autores)]
    if g1:
        md.append("![último día](resultados/ultimo_dia.png)\n")
    md += ["## 🧪 Backtest (días pasados, para arrancar en frío)\n",
           "_Ojo: en el backtest el 'pronóstico' de clima es casi el clima observado → resultados optimistas._\n",
           _tabla_md(t_bt, autores)]
    if g2:
        md.append("![backtest](resultados/backtest.png)\n")
    (RAIZ / "LEADERBOARD.md").write_text("\n".join(md), encoding="utf-8")
    print("\n" + "\n".join(md))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true")
    ap.add_argument("--backtest", type=int, default=0)
    ap.add_argument("--sin-descarga", action="store_true", help="usa datos/ ya cacheados")
    a = ap.parse_args()
    RES.mkdir(exist_ok=True)
    PRED.mkdir(exist_ok=True)
    hist, clima = datos.cargar() if a.sin_descarga else datos.actualizar(demo=a.demo)
    modelos = cargar_modelos()
    print(f"Modelos en la liga: {', '.join(modelos)}")
    predecir_manana(hist, clima, modelos)
    if a.backtest:
        backtest(hist, clima, modelos, a.backtest)
    leaderboard(hist, modelos)


if __name__ == "__main__":
    main()
