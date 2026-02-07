# Cambios Implementados - Sistema Multi-Proyecto

Fecha: 2026-02-07

## 🎯 Objetivo

Transformar Platform de analizar 1 proyecto (Arbitrum) a **10 proyectos simultáneamente**, con arquitectura extensible para añadir más fuentes (Twitter, Reddit, onchain).

---

## 📦 Archivos Nuevos Creados

### 1. `projects.yaml` 
**Propósito:** Configuración centralizada de los 10 proyectos

**Contenido:**
- **Layer 1:** Ethereum, Solana
- **Layer 2:** Arbitrum, Optimism
- **DeFi:** Uniswap, Aave
- **Infrastructure:** Chainlink, The Graph
- **Emerging:** EigenLayer, Celestia

**Estructura extensible:**
```yaml
github:        # ✅ ACTIVO - Se procesa ahora
  repositories: [...]
  
social:        # 🔴 FUTURO - Preparado pero no implementado
  twitter: [...]
  reddit: [...]
  
onchain:       # 🔴 FUTURO - Preparado pero no implementado
  networks: [...]
```

### 2. `setup_all_projects.py`
**Propósito:** Insertar todos los proyectos en la BD automáticamente

**Funcionalidad:**
- Lee `projects.yaml`
- Crea registros en `projects` table
- Crea registros en `sources` table (GitHub repos)
- **Idempotente** - Seguro ejecutar múltiples veces
- Logs detallados de progreso

**Uso:**
```bash
python setup_all_projects.py
```

### 3. `run_all_projects.py`
**Propósito:** Ejecutar pipeline para múltiples proyectos en batch

**Funcionalidad:**
- Procesa todos los proyectos de `projects.yaml`
- Para cada proyecto ejecuta: Ingest → Normalize → Insights
- Manejo de errores por proyecto (continúa si uno falla)
- Delay de 2s entre proyectos (rate limiting)
- Logs detallados + resumen final

**Opciones:**
```bash
# Todos los proyectos
python run_all_projects.py --days 7

# Solo algunos
python run_all_projects.py --only ethereum solana --days 7

# Sin AI insights
python run_all_projects.py --skip-insights --days 7
```

### 4. `init_container.sh`
**Propósito:** Script de inicialización para contenedor Docker

**Funcionalidad:**
- Espera a que PostgreSQL esté listo
- Ejecuta `setup_all_projects.py` (setup automático)
- Ejecuta `run_all_projects.py` (pipeline)
- Manejo de errores + logs claros

### 5. `docs/MULTI_PROJECT_GUIDE.md`
**Propósito:** Documentación completa del sistema multi-proyecto

**Contenido:**
- Guía de uso
- Estructura de `projects.yaml`
- Comandos útiles
- Troubleshooting
- Roadmap de futuras fuentes (Twitter, Reddit, onchain)

---

## 🔧 Archivos Modificados

### 1. `Dockerfile`
**Cambios:**
- Añadido `chmod +x init_container.sh`
- CMD cambiado a `./init_container.sh --days 7`
- Ahora ejecuta setup automático al iniciar

### 2. `docker-compose.dev.yml` (en Support)
**Cambios:**
- `platform-app.command` → `./init_container.sh --days 7`
- Comentario actualizado: "Processes all 10 projects"

### 3. `README.md`
**Cambios:**
- Sección "Multi-Project Pipeline" añadida
- Links a `MULTI_PROJECT_GUIDE.md`
- Aclaración de archivos legacy vs nuevos

---

## 📊 Arquitectura Resultante

```
┌─────────────────────────────────────┐
│    projects.yaml (10 proyectos)    │
└──────────────┬──────────────────────┘
               │
               ↓
┌──────────────────────────────────────┐
│   setup_all_projects.py             │
│   (Inserta en BD - una sola vez)    │
└──────────────┬───────────────────────┘
               │
               ↓
┌──────────────────────────────────────┐
│      PostgreSQL Database             │
│   ┌─────────────┐  ┌──────────┐    │
│   │  projects   │  │ sources  │    │
│   │ (10 filas)  │  │(~15 filas)│    │
│   └─────────────┘  └──────────┘    │
└──────────────┬───────────────────────┘
               │
               ↓
┌──────────────────────────────────────┐
│   run_all_projects.py               │
│   (Procesa todos en batch)          │
└──────────────┬───────────────────────┘
               │
     ┌─────────┼─────────┐
     ↓         ↓         ↓
  Ethereum  Solana  Arbitrum ... (×10)
     │         │         │
     ↓         ↓         ↓
 ┌────────────────────────┐
 │  GitHub Ingestion      │
 │  ↓                     │
 │  Event Normalization   │
 │  ↓                     │
 │  AI Insights (ES+EN)   │
 └────────────────────────┘
```

---

## 🎯 Beneficios

### ✅ Escalabilidad
- Añadir proyectos = editar YAML + re-run setup
- No requiere cambios de código

### ✅ Modularidad
- Campos `social` y `onchain` ya definidos
- Futuras fuentes = nuevo script en `ingestion/`
- Mismo flujo: Ingest → Normalize → Insights

### ✅ Mantenibilidad
- Configuración centralizada en `projects.yaml`
- Un solo punto de verdad
- Scripts reutilizables

### ✅ Docker-Ready
- Inicialización automática
- Setup + Pipeline en un comando
- Contenedor autónomo

---

## 🔮 Roadmap - Próximas Implementaciones

### 1. Twitter Ingestion
```python
# ingestion/twitter/ingest_twitter.py
def main():
    projects = load_projects_yaml()
    for project in projects:
        for twitter in project.get("social", {}).get("twitter", []):
            fetch_tweets(twitter["handle"])
            insert_raw_events(...)
```

### 2. Reddit Ingestion
```python
# ingestion/reddit/ingest_reddit.py
def main():
    projects = load_projects_yaml()
    for project in projects:
        for reddit in project.get("social", {}).get("reddit", []):
            fetch_posts(reddit["subreddit"])
            insert_raw_events(...)
```

### 3. Onchain Ingestion
```python
# ingestion/onchain/ingest_onchain.py
def main():
    projects = load_projects_yaml()
    for project in projects:
        for network in project.get("onchain", {}).get("networks", []):
            fetch_transactions(network)
            insert_raw_events(...)
```

**Patrón común:**
- Leer `projects.yaml`
- Extraer configuración específica (`github`, `social`, `onchain`)
- Ingestar a `raw_events`
- Normalización común en `normalize.py`
- Insights comunes en `generate_insights.py`

---

## 🚀 Cómo Usar

### Local (Desarrollo)

```bash
# 1. Setup inicial (una vez)
python setup_all_projects.py

# 2. Ejecutar pipeline
python run_all_projects.py --days 7

# 3. Solo algunos proyectos
python run_all_projects.py --only ethereum solana
```

### Docker (Producción)

```bash
# Desde Support/
docker-compose -f docker-compose.dev.yml up -d

# Ver logs
docker logs -f cip-platform

# El contenedor automáticamente:
# 1. Espera PostgreSQL
# 2. Ejecuta setup_all_projects.py
# 3. Ejecuta run_all_projects.py --days 7
```

---

## 📝 Notas Importantes

### Archivos Legacy (Mantener por compatibilidad)
- `project.yaml` - Configuración single-project (Arbitrum)
- `run_pipeline.py` - Pipeline single-project
- `add_project.py` - Añadir proyecto individual

**Deprecados pero funcionales** - Útiles para testing de un proyecto

### Rate Limiting
- GitHub API: 5000 req/h con token (60 sin token)
- Script añade 2s delay entre proyectos
- ~10 proyectos × ~10 requests = ~100 requests totales
- **Suficiente para ejecución frecuente**

### AI Insights Cost
- OpenAI GPT-4o-mini: ~$0.15 / 1M tokens input, ~$0.60 / 1M output
- 10 proyectos × ~1000 tokens/insight = ~$0.001 por ejecución
- **Muy económico**

---

## ✅ Testing Checklist

- [ ] `python setup_all_projects.py` ejecuta sin errores
- [ ] 10 proyectos insertados en tabla `projects`
- [ ] ~15 sources insertados en tabla `sources`
- [ ] `python run_all_projects.py --only ethereum` funciona
- [ ] `docker-compose up` levanta platform correctamente
- [ ] Logs muestran procesamiento de múltiples proyectos
- [ ] API devuelve datos de múltiples proyectos
- [ ] Web muestra insights de múltiples proyectos

---

## 🎉 Resultado Final

**ANTES:**
- 1 proyecto (Arbitrum)
- 1 archivo YAML
- Ejecución manual por proyecto

**DESPUÉS:**
- 10 proyectos simultáneos
- 1 archivo YAML centralizado
- Ejecución automática en batch
- Arquitectura extensible para más fuentes
- Docker totalmente automatizado

**Preparado para escalar a 50+ proyectos y múltiples fuentes de datos** 🚀
