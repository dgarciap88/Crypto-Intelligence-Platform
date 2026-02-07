# Multi-Project Pipeline Guide

Esta guía explica cómo usar el nuevo sistema de análisis multi-proyecto.

## 📋 Arquitectura

### Archivos Clave

- **`projects.yaml`** - Configuración de todos los proyectos a analizar
- **`setup_all_projects.py`** - Inserta proyectos en la BD
- **`run_all_projects.py`** - Ejecuta pipeline para todos los proyectos
- **`add_project.py`** - [Legacy] Añadir un proyecto individual
- **`run_pipeline.py`** - [Legacy] Ejecutar pipeline para un proyecto

## 🚀 Uso Básico

### 1. Configurar Proyectos en BD (una sola vez)

```bash
# Insertar todos los proyectos de projects.yaml en la base de datos
python setup_all_projects.py
```

Esto crea:
- Registros en tabla `projects`
- Registros en tabla `sources` (GitHub repos)

### 2. Ejecutar Pipeline para Todos

```bash
# Procesar todos los proyectos
python run_all_projects.py --days 7

# Solo ingestión + normalización (sin IA)
python run_all_projects.py --days 7 --skip-insights

# Solo normalización + IA (sin ingestión)
python run_all_projects.py --days 7 --skip-ingest
```

### 3. Procesar Solo Algunos Proyectos

```bash
# Solo Ethereum y Solana
python run_all_projects.py --days 7 --only ethereum solana

# Solo un proyecto
python run_all_projects.py --days 7 --only arbitrum
```

## 🐳 Uso con Docker

### Levantar Stack Completo

```bash
# Desde Support/
docker-compose -f docker-compose.dev.yml up -d

# Ver logs de Platform
docker logs -f cip-platform
```

El contenedor **automáticamente**:
1. Espera a que PostgreSQL esté listo
2. Ejecuta `setup_all_projects.py` (si es primera vez)
3. Ejecuta `run_all_projects.py --days 7`
4. Procesa los 10 proyectos secuencialmente

### Rebuild Después de Cambios

```bash
# Rebuild solo Platform
docker-compose -f docker-compose.dev.yml build platform-app

# Recrear y levantar
docker-compose -f docker-compose.dev.yml up -d --build platform-app
```

## 📂 Estructura de projects.yaml

```yaml
projects:
  - project_id: ethereum      # ID único (minúsculas, sin espacios)
    name: Ethereum            # Nombre display
    category: layer1          # Categoría (layer1, layer2, defi, etc)
    description: "..."        # Descripción corta
    
    token:
      symbol: ETH             # Símbolo del token
      network: ethereum       # Red principal
    
    github:                   # 🟢 ACTIVO - Se analiza
      repositories:
        - owner: ethereum
          repo: go-ethereum
        - owner: ethereum
          repo: consensus-specs
    
    social:                   # 🔴 NO ACTIVO - Futuro
      twitter:
        - handle: ethereum
      reddit:
        - subreddit: ethereum
    
    onchain:                  # 🔴 NO ACTIVO - Futuro
      networks:
        - ethereum
```

### Campos Activos vs Futuros

| Campo | Estado | Uso |
|-------|--------|-----|
| `github.repositories` | ✅ **ACTIVO** | Se ingestan commits y releases |
| `social.twitter` | 🔴 Futuro | Preparado pero no implementado |
| `social.reddit` | 🔴 Futuro | Preparado pero no implementado |
| `onchain.networks` | 🔴 Futuro | Preparado pero no implementado |

## ➕ Añadir un Nuevo Proyecto

### Opción A: Editar projects.yaml (RECOMENDADO)

```yaml
projects:
  # ... proyectos existentes ...
  
  - project_id: polygon
    name: Polygon
    category: layer2
    description: Ethereum scaling solution
    token:
      symbol: MATIC
      network: ethereum
    github:
      repositories:
        - owner: maticnetwork
          repo: bor
```

Luego ejecutar:
```bash
python setup_all_projects.py   # Actualiza BD
python run_all_projects.py --only polygon --days 7
```

### Opción B: Script add_project.py

```bash
python add_project.py \
  --project-id polygon \
  --name Polygon \
  --category layer2 \
  --token MATIC \
  --github-repos maticnetwork/bor
```

## 🔄 Pipeline Stages

Para cada proyecto, el pipeline ejecuta 3 stages:

### 1. GitHub Ingestion
- Lee `github.repositories` de projects.yaml
- Fetches commits y releases desde GitHub API
- Inserta en tabla `raw_events`
- **Requiere:** `GITHUB_TOKEN`

### 2. Event Normalization
- Lee `raw_events` sin procesar
- Normaliza a schema común
- Inserta en tabla `normalized_events`

### 3. AI Insights Generation
- Analiza eventos recientes (últimos N días)
- Genera insights con OpenAI GPT-4o-mini
- Genera versiones ES + EN simultáneamente
- Inserta en tabla `ai_insights`
- **Requiere:** `OPENAI_API_KEY`

## 🔧 Variables de Entorno

```bash
# Requeridas
DATABASE_URL=postgresql://user:pass@host:5432/dbname

# Opcionales pero recomendadas
GITHUB_TOKEN=ghp_xxxx              # Mayor rate limit
OPENAI_API_KEY=sk-xxxx             # Para insights
OPENAI_MODEL=gpt-4o-mini           # Modelo a usar
```

## 🎯 Proyectos Actuales

Los 10 proyectos configurados:

| Category | Project | Repos |
|----------|---------|-------|
| **Layer 1** | Ethereum | ethereum/go-ethereum, ethereum/consensus-specs |
| | Solana | solana-labs/solana |
| **Layer 2** | Arbitrum | OffchainLabs/arbitrum, OffchainLabs/nitro |
| | Optimism | ethereum-optimism/optimism |
| **DeFi** | Uniswap | Uniswap/v3-core, Uniswap/interface |
| | Aave | aave/aave-v3-core |
| **Infrastructure** | Chainlink | smartcontractkit/chainlink |
| | The Graph | graphprotocol/graph-node |
| **Emerging** | EigenLayer | Layr-Labs/eigenlayer-contracts |
| | Celestia | celestiaorg/celestia-node |

## 📊 Monitoreo

### Ver Proyectos en BD

```sql
SELECT project_id, name, category, token_symbol 
FROM projects 
ORDER BY category, project_id;
```

### Ver Sources por Proyecto

```sql
SELECT p.project_id, p.name, s.source_type, s.reference
FROM projects p
JOIN sources s ON s.project_id = p.id
ORDER BY p.project_id, s.source_type;
```

### Ver Eventos por Proyecto

```sql
SELECT p.project_id, COUNT(*) as total_events
FROM normalized_events ne
JOIN projects p ON p.id = ne.project_id
GROUP BY p.project_id
ORDER BY total_events DESC;
```

### Ver Insights por Proyecto

```sql
SELECT p.project_id, COUNT(*) as total_insights
FROM ai_insights ai
JOIN projects p ON p.id = ai.project_id
GROUP BY p.project_id
ORDER BY total_insights DESC;
```

## 🚨 Troubleshooting

### "GITHUB_TOKEN not set"
```bash
# Genera token en: https://github.com/settings/tokens
export GITHUB_TOKEN=ghp_xxxxx
```

### "OPENAI_API_KEY not set"
```bash
# Obtén key en: https://platform.openai.com/api-keys
export OPENAI_API_KEY=sk-xxxxx
```

### Pipeline falla en un proyecto
```bash
# El pipeline continúa con el resto
# Revisar logs para ver qué proyecto falló
# Re-ejecutar solo ese proyecto:
python run_all_projects.py --only <project_id> --days 7
```

### Rate limit de GitHub
```bash
# Usar GITHUB_TOKEN aumenta límite de 60/hr a 5000/hr
# O añadir delay entre proyectos (ya incluido: 2 segundos)
```

## 🔮 Roadmap - Próximas Fuentes

### Twitter (Planeado)
```python
# ingestion/twitter/ingest_twitter.py
# Lee social.twitter de projects.yaml
# Fetches tweets usando Twitter API v2
```

### Reddit (Planeado)
```python
# ingestion/reddit/ingest_reddit.py
# Lee social.reddit de projects.yaml
# Fetches posts usando PRAW
```

### On-chain (Planeado)
```python
# ingestion/onchain/ingest_onchain.py
# Lee onchain.networks de projects.yaml
# Fetches transactions usando Etherscan/etc
```

Cada fuente sigue el mismo patrón:
1. Lee config de `projects.yaml`
2. Ingesta a `raw_events`
3. Normalización crea `normalized_events`
4. IA genera `ai_insights`

## 📚 Referencias

- Schema: `../Support/db/create_tables.sql`
- API: `../API/` para consultar datos procesados
- Web: `../Web/` para visualizar en frontend
- Docs: `../Support/docs/` para especificaciones
