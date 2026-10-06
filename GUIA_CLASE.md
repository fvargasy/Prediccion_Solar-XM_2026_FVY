# Guía de clase — Deep Learning para energías renovables con la API de XM

**Duración sugerida:** 2 h · **Prerrequisito:** clase anterior (API de Datos Abiertos Colombia) y cuenta de GitHub.

| Tiempo | Bloque | Qué pasa |
|---|---|---|
| 0:00–0:15 | **Gancho** | Mostrar `LEADERBOARD.md` y la gráfica. Pregunta: *¿cuánta energía solar generará Colombia mañana a las 11 a. m.? Apuesten un número.* |
| 0:15–0:35 | **La API de XM en vivo** | Mostrar el repo oficial [EquipoAnaliticaXM/API_XM](https://github.com/EquipoAnaliticaXM/API_XM). En Colab: `pip install pydataxm`, `ReadDB().get_collections()` para ver las métricas, `request_data("ListadoRecursos","Sistema",…)` → filtrar `RAD SOLAR`, `request_data("Gene","Recurso",…)`. Discutir: rezago de publicación, consultas por mes en paralelo, kWh→MWh. |
| 0:35–0:50 | **Por qué necesitamos el clima** | Persistencia vs Persistencia × radiación. La serie sola no sabe que mañana llueve en el Cesar. |
| 0:50–1:15 | **SolarNet-GRU** | Recorrer `modelos/solarnet_gru.py`: features por hora, GRU bidireccional, ReLU de salida (generación ≥ 0), re-entrenamiento diario (online learning), mismo rezago en entrenamiento y predicción. |
| 1:15–1:30 | **GitHub como laboratorio** | Fork → nuevo archivo en `modelos/` → PR → pestaña *Actions* valida el modelo → merge. Mostrar el cron de `pronostico_diario.yml`. |
| 1:30–1:50 | **Manos a la obra** | En parejas: copiar `_plantilla.py` y mejorar algo (ver retos). Probar con `--demo --backtest 5`. Abrir el PR antes de salir. |
| 1:50–2:00 | **Claude como analista** | En un issue: `@claude ¿por qué la persistencia falla tanto en días nublados?` (o lo mismo desde Cowork con el repo). |

## Retos para los estudiantes (de menor a mayor)
1. Cambiar la persistencia por el promedio de los últimos 3 días a esa hora.
2. Agregar a SolarNet la nubosidad de la hora anterior y la siguiente (contexto temporal del clima).
3. Pérdida ponderada: que el error del mediodía pese más (ahí están los MWh).
4. Reemplazar la GRU por un Transformer pequeño (2 cabezas, 1 capa) o un 1D-CNN.
5. Ensamble de 5 semillas y medir si baja la varianza del error.
6. **Pro:** predecir intervalos (cuantiles 10–50–90) con pinball loss.

## Preguntas de discusión
- ¿Por qué el backtest se ve mejor que la liga oficial? (el "pronóstico" de clima pasado es casi observación)
- Si entra un parque solar de 200 MW nuevo, ¿qué le pasa al modelo? ¿Cómo lo arreglarían?
- ¿Por qué evaluamos solo 06–18 h?

## Antes de la clase (profe, 10 min)
1. Crear el repo en GitHub y subir esta carpeta.
2. *Actions* → *☀️ Pronóstico diario* → **Run workflow** con `backtest = 14` para que el leaderboard ya tenga datos.
3. (Opcional) *Settings → Secrets → Actions*: `ANTHROPIC_API_KEY` para habilitar `@claude`.
