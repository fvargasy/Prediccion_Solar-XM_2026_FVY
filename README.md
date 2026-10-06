# ☀️ Liga de Pronóstico Solar Colombia

**Un Kaggle vivo con datos reales del sistema eléctrico colombiano.**
Cada mañana, GitHub Actions descarga la generación solar real de **XM** y el pronóstico del
tiempo de **Open-Meteo**, re-entrena una red neuronal, **pronostica la generación solar nacional
de mañana hora a hora** y califica a todos los modelos de la clase contra lo que realmente pasó.
El `LEADERBOARD.md` se actualiza solo.

> Tu misión: escribir un modelo que le gane a la persistencia… y al modelo del profe (`SolarNet-GRU`).

## ¿Cómo funciona?

```
 07:00 COL  ┌───────────────┐   ┌────────────────┐   ┌──────────────────┐   ┌───────────────┐
 (cron) ──▶ │ pydataxm (XM) │──▶│ Open-Meteo     │──▶│ Todos los modelos│──▶│ Calificación  │
            │ Gene×Recurso  │   │ radiación,     │   │ de modelos/*.py  │   │ vs dato real  │
            │ filtra SOLAR  │   │ nubes, temp.   │   │ predicen mañana  │   │ → LEADERBOARD │
            └───────────────┘   └────────────────┘   └──────────────────┘   └───────────────┘
```

- **Objetivo:** generación solar total del SIN (MWh), 24 horas del día siguiente.
- **Métrica:** MAE en horas de sol (06–18 h). **Skill** = 1 − MAE/MAE_persistencia.
- **Anti-trampa:** la primera predicción de cada día queda congelada en `predicciones/AAAA-MM-DD.csv`
  (el historial de git lo demuestra). XM publica con 1–2 días de rezago, así que el dato real llega después.

## Participar (estudiantes)

1. Haz **fork** de este repositorio.
2. Copia `modelos/_plantilla.py` como `modelos/<tu_usuario>.py` y escribe tu `predecir(historia, clima_dia)`.
3. Pruébalo localmente: `python -m liga.run_diario --demo --backtest 5`
4. Abre un **Pull Request**. El workflow *Validar modelos* lo prueba automáticamente.
5. Cuando el profe lo aprueba (merge), tu modelo compite desde la mañana siguiente.

## Correr localmente / en Colab

```bash
pip install -r requirements.txt
python -m liga.run_diario --demo --backtest 7     # sin internet, datos sintéticos
python -m liga.run_diario --backtest 14           # datos reales de XM + Open-Meteo
```

En Colab: `!git clone https://github.com/<usuario>/liga-solar-xm && %cd liga-solar-xm` y los mismos comandos con `!`.

## Estructura

| Carpeta | Qué hay |
|---|---|
| `liga/xm.py` | Descarga de XM con **pydataxm**, la librería oficial de XM ([EquipoAnaliticaXM/API_XM](https://github.com/EquipoAnaliticaXM/API_XM)) |
| `liga/clima.py` | Open-Meteo en 4 núcleos solares (Cesar, Atlántico-Bolívar, Tolima, Córdoba-Sucre) |
| `liga/datos.py` | Arma el dataset, limpia días incompletos, modo `--demo` sintético |
| `liga/run_diario.py` | Orquesta: predicción oficial, backtest, calificación, leaderboard y gráficas |
| `modelos/` | Un archivo `.py` por participante (los que empiezan por `_` se ignoran) |
| `predicciones/` | Predicciones oficiales congeladas, una por día |
| `.github/workflows/` | Pronóstico diario (cron), validación de PRs y Claude como analista |

## Claude como analista de la liga (opcional)

Con el secreto `ANTHROPIC_API_KEY` configurado, cualquiera puede escribir en un issue o PR:

- `@claude ¿por qué todos los modelos fallaron ayer? revisa el clima y los datos`
- `@claude revisa mi modelo y dime cómo reducir el error en la tarde`
- `@claude agrega la irradiancia de la hora anterior como feature a SolarNet-GRU y abre un PR`

Las instrucciones que Claude sigue están en `CLAUDE.md`.

## Fuentes de datos

- **XM** — librería oficial `pydataxm` ([github.com/EquipoAnaliticaXM/API_XM](https://github.com/EquipoAnaliticaXM/API_XM)), que consulta la API pública `servapibi.xm.com.co`. Usamos `ReadDB().request_data("Gene", "Recurso", …)` (generación real horaria, kWh) y `request_data("ListadoRecursos", "Sistema", …)` filtrando `EnerSource = RAD SOLAR`.
- **Open-Meteo** — pronóstico meteorológico abierto (`api.open-meteo.com`), radiación de onda corta, nubosidad y temperatura.
