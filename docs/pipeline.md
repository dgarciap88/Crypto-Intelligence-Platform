# Data Pipeline - CIP

## Overview

El **Crypto Intelligence Platform** implementa un pipeline modular en 3 etapas:

```
1. INGEST → 2. NORMALIZE → 3. INSIGHTS
```

---

## 1. Ingestion (Raw Events)

**Objetivo:** Capturar datos crudos de diferentes fuentes sin filtrar ni transformar.

### GitHub Ingestion

Script: `ingestion/github/ingest_github.py`

**Funcionalidad:**
- Lee configuración de `project.yaml`
- Para cada repositorio listado:
  - Obtiene commits (últimos 100)
  - Obtiene releases (últimos 100)
- Almacena todo en `raw_events` con payloads completos
- **Idempotente:** usa campos `unique_id` para evitar duplicados

**Uso:**
```bash
export DATABASE_URL="postgresql://user:pass@localhost:5432/cip"
export GITHUB_TOKEN="ghp_..."  # opcional
python ingestion/github/ingest_github.py --project ./project.yaml
```

**Tablas involucradas:**
- `projects` - Registro del proyecto
- `sources` - Fuentes (repos GitHub)
- `raw_events` - Eventos sin procesar

---

## 2. Normalization

Script: `ingestion/normalize.py`

**Objetivo:** Transformar eventos crudos en estructura uniforme y consultar fácilmente.

**Funcionalidad:**
- Lee `raw_events` que no han sido normalizados
- Extrae campos comunes: `entity_type`, `entity_id`, `title`, `description`
- Guarda en `normalized_events` con relación a `raw_event_id`
- **Idempotente:** constraint UNIQUE en `raw_event_id`

**Uso:**
```bash
export DATABASE_URL="postgresql://user:pass@localhost:5432/cip"
python ingestion/normalize.py --project-id arbitrum --batch-size 100
```

**Tablas involucradas:**
- `normalized_events` - Eventos estructurados

**Campos normalizados:**
| Campo | Descripción |
|-------|-------------|
| `entity_type` | commit, release, tweet, transaction |
| `entity_id` | SHA, release_id, tweet_id, tx_hash |
| `title` | Título corto del evento |
| `description` | Descripción extendida |
| `metadata` | Campos adicionales específicos del tipo |

---

## 3. AI Insights

Script: `ingestion/generate_insights.py`

**Objetivo:** Generar análisis y resúmenes usando IA (no predicciones).

**Funcionalidad:**
- Lee eventos normalizados de los últimos N días
- Agrupa por tipo y formatea para el LLM
- Genera resumen usando OpenAI API (gpt-4o-mini)
- Almacena en `ai_insights` con referencias a eventos fuente

**Uso:**
```bash
export DATABASE_URL="postgresql://user:pass@localhost:5432/cip"
export OPENAI_API_KEY="sk-..."
python ingestion/generate_insights.py --project-id arbitrum --days 7
```

**Características:**
- No regenera si hay insight reciente (últimas 12h)
- Usa `--force` para forzar regeneración
- Guarda IDs de eventos fuente (hasta 50)
- Agrega metadata con conteo y timestamp

**Tablas involucradas:**
- `ai_insights` - Insights generados

---

## Pipeline Completo

**Ejemplo de ejecución completa:**

```bash
# 1. Ingestar datos de GitHub
python ingestion/github/ingest_github.py --project ./project.yaml

# 2. Normalizar eventos
python ingestion/normalize.py --project-id arbitrum

# 3. Generar insights
python ingestion/generate_insights.py --project-id arbitrum --days 7
```

---

## Próximos Pasos

### Extensiones planificadas:
1. **Más fuentes:**
   - Twitter/X ingestion
   - Reddit ingestion
   - On-chain data (transactions, events)

2. **Señales técnicas:**
   - Detección de patrones (aumento de commits, releases frecuentes)
   - Alertas automáticas

3. **Scheduler:**
   - Cron jobs o Airflow para ejecución automática
   - Pipeline diario/semanal

4. **API:**
   - FastAPI endpoint para consultar insights
   - Dashboard web (opcional)

---

## Reglas de Diseño

✅ **DO:**
- Mantener scripts independientes y modulares
- Cada etapa es idempotente (se puede re-ejecutar)
- Logging claro de operaciones
- Tipos y docstrings en Python

❌ **DON'T:**
- No predecir precios ni señales de trading
- No filtrar datos en ingestion (guardar todo)
- No acoplar scripts (cada uno debe funcionar solo)
