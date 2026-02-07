# Crypto Intelligence Platform (CIP)

**Backend-first platform for crypto project intelligence**  
Ingestion → Normalization → AI Insights

🎯 **Analiza 10 proyectos crypto simultáneamente** (Ethereum, Solana, Arbitrum, y más)

---

## 🎯 Objective

Build a modular data platform that:
- **Ingests** data from multiple sources (GitHub, Twitter, onchain)
- **Normalizes** events into structured format
- **Generates insights** using AI (summaries, patterns, trends)
- **Scales** to analyze multiple projects simultaneously

**What it does NOT do:** Price predictions, trading signals, financial advice.

---

## 📁 Project Structure

```
Crypto-Intelligence-Platform/
├── docs/
│   ├── MULTI_PROJECT_GUIDE.md # 📖 Multi-project guide (START HERE)
│   ├── pipeline.md            # Pipeline documentation
│   ├── project-schema.md      # Project YAML schema
│   └── db-schema.md           # Database schema details
├── ingestion/
│   ├── github/
│   │   └── ingest_github.py   # GitHub data ingestion
│   ├── normalize.py           # Event normalization
│   └── generate_insights.py   # AI insights generation
├── projects.yaml              # 🆕 All 10 projects configuration
├── setup_all_projects.py      # 🆕 Setup all projects in DB
├── run_all_projects.py        # 🆕 Run pipeline for all projects
├── project.yaml               # [Legacy] Single project (Arbitrum)
├── run_pipeline.py            # [Legacy] Single project pipeline
├── requirements.txt           # Python dependencies
└── .env.example               # Environment variables template
```

---

## 🚀 Quick Start

> 💡 **Para stack completo** (Platform + API + Web), ver [Crypto-Intelligence-Platform-Support](../Crypto-Intelligence-Platform-Support)

### Environment Variables

```bash
# Copy template and edit with your credentials
cp .env.example .env
```

**Required Variables:**

| Variable | Description | Get From |
|----------|-------------|----------|
| `DATABASE_URL` | PostgreSQL connection string | Docker default: `postgresql://crypto_user:crypto_pass_dev@localhost:5432/crypto_intel` |
| `GITHUB_TOKEN` | GitHub Personal Access Token | [github.com/settings/tokens](https://github.com/settings/tokens) (scopes: `repo`, `read:org`) |
| `OPENAI_API_KEY` | OpenAI API Key | [platform.openai.com/api-keys](https://platform.openai.com/api-keys) |
| `GITHUB_UPDATE_INTERVAL_MINUTES` | Minutes between GitHub updates (default: 360 = 6 hours) | Optional |
| `TWITTER_UPDATE_INTERVAL_MINUTES` | Minutes between Twitter updates (default: 30) | Optional |
| `ONCHAIN_UPDATE_INTERVAL_MINUTES` | Minutes between on-chain updates (default: 15) | Optional |
| `CHECK_INTERVAL_SECONDS` | Seconds between schedule checks (default: 60) | Optional |

### Multi-Project Pipeline

**🔄 Modo Continuo (RECOMENDADO para Producción):**

El sistema ejecuta actualizaciones automáticas con diferentes frecuencias según la fuente de datos:
- **GitHub**: cada 6 horas (respeta rate limits)
- **Twitter**: cada 30 minutos (cuando se implemente)
- **On-chain**: cada 15 minutos (cuando se implemente)

```bash
# 1. Configurar environment
cp .env.example .env
# Edit .env with your credentials

# 2. Insertar 10 proyectos en BD
python setup_all_projects.py

# 3. Ejecutar pipeline en modo continuo
python run_all_projects.py --continuous

# Personalizar frecuencias en .env:
# GITHUB_UPDATE_INTERVAL_MINUTES=180  # 3 horas en vez de 6
```

**⚡ Modo Una Vez (para desarrollo/testing):**

```bash
# Ejecutar pipeline para todos los proyectos (una sola vez)
python run_all_projects.py --days 7

# 4. Ejecutar solo algunos proyectos
python run_all_projects.py --only ethereum solana --days 7
```

📖 **Ver [docs/MULTI_PROJECT_GUIDE.md](docs/MULTI_PROJECT_GUIDE.md) para guía completa**

### Docker - Stack Completo (Platform + API + Web)

```bash
# Desde ../Crypto-Intelligence-Platform-Support/
docker-compose -f docker-compose.dev.yml up -d

# Ver logs
docker logs -f cip-platform

# Acceder al stack:
# - Web UI: http://localhost:5173
# - API: http://localhost:8000/docs
# - PostgreSQL: localhost:5432
```

### Pipeline Individual (Legacy)

```bash
# 1. Configurar environment
cp .env.example .env
# Editar .env con tus valores

# 2. Iniciar con Docker Compose
docker-compose up -d

# 3. Ejecutar pipeline
docker-compose exec app python run_pipeline.py --project-id arbitrum --days 7

# 4. Ver insights
docker-compose exec app python query_insights.py --project-id arbitrum
```

📖 **Ver [docs/DOCKER.md](docs/DOCKER.md) para guía completa de Docker (desarrollo)**  
📖 **Para producción:** [Support/docs/DOCKER-PRODUCTION.md](../Crypto-Intelligence-Platform-Support/docs/DOCKER-PRODUCTION.md)

### Opción 2: Local (Python)

#### 1. Setup Database

```bash
# Create PostgreSQL database
createdb crypto_intel

# Run schema (desde el proyecto Support)
psql crypto_intel -f ../Crypto-Intelligence-Platform-Support/db/create_tables.sql
```

#### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

#### 3. Configure Environment

```bash
cp .env.example .env
# Edit .env with your credentials:
# - DATABASE_URL
# - GITHUB_TOKEN (optional)
# - OPENAI_API_KEY
```

#### 4. Run Pipeline

```bash
# Step 1: Ingest GitHub data
python ingestion/github/ingest_github.py --project ./project.yaml

# Step 2: Normalize events
python ingestion/normalize.py --project-id arbitrum

# Step 3: Generate AI insights
python ingestion/generate_insights.py --project-id arbitrum --days 7
```

---

## 📊 Database Schema

**⚠️ NOTA:** Los schemas de la base de datos ahora están centralizados en el proyecto **Support**.  
Ver: `Crypto-Intelligence-Platform-Support/db/create_tables.sql`

### Core Tables

| Table | Purpose |
|-------|---------|
| `projects` | Crypto projects being tracked |
| `sources` | Data sources (repos, accounts, contracts) |
| `raw_events` | Unprocessed events with full payloads |
| `normalized_events` | Structured events (entity_type, title, description) |
| `ai_insights` | AI-generated summaries and analysis (multi-idioma: ES/EN) |

Ver [db-schema.md](docs/db-schema.md) para detalles o el README en `Support/db/README.md`.

---

## 🔧 Components

### 1. GitHub Ingestion
- Fetches commits and releases from configured repositories
- Stores raw data in `raw_events`
- **Idempotent:** uses unique IDs to avoid duplicates

**Script:** `ingestion/github/ingest_github.py`

### 2. Normalization
- Transforms raw events into uniform structure
- Extracts: entity_type, entity_id, title, description
- Makes data easier to query and analyze

**Script:** `ingestion/normalize.py`

### 3. AI Insights
- Analyzes normalized events using OpenAI API
- Generates summaries of development activity
- NO price predictions, only factual analysis

**Script:** `ingestion/generate_insights.py`

See [pipeline.md](docs/pipeline.md) for detailed documentation.

---

## 🎨 Design Principles

✅ **Backend-first** - Focus on data pipelines, not UI  
✅ **Modular** - Each component is independent  
✅ **Idempotent** - Scripts can be safely re-run  
✅ **Testeable** - Clear functions with types  
✅ **Documented** - Comments and docstrings  

❌ **No price predictions**  
❌ **No trading signals**  
❌ **No financial advice**  

---

## 📝 Project Configuration

Projects are defined in YAML format. Example:

```yaml
project_id: arbitrum
name: Arbitrum
category: layer2

token:
  symbol: ARB

github:
  repositories:
    - owner: OffchainLabs
      repo: arbitrum
```

See [project-schema.md](docs/project-schema.md) for full schema.

---

## 🔮 Roadmap

### Current Status ✅
- [x] PostgreSQL schema with indexes
- [x] GitHub ingestion (commits, releases)
- [x] Event normalization pipeline
- [x] AI insights generation
- [x] Docker development setup
- [x] Docker production setup (en Support)

### Next Steps 🚧
- [ ] Twitter/X ingestion
- [ ] Reddit ingestion
- [ ] On-chain data ingestion
- [ ] Technical signals (commit frequency, release patterns)
- [ ] Automated scheduling (cron/Airflow)
- [ ] REST API (FastAPI)
- [ ] Dashboard (optional)

---

## 🏗️ Proyectos Relacionados

### Crypto-Intelligence-Platform-Support
Repositorio de **infraestructura y operaciones**:
- Docker Compose de producción
- PostgreSQL optimizado
- Kubernetes manifests
- Scripts de backup/restore/deploy
- Documentación de deployment

🔗 [Ver Support Project](../Crypto-Intelligence-Platform-Support
- [ ] Dashboard (optional)

---

## 🛠️ Tech Stack

- **Language:** Python 3.11+
- **Database:** PostgreSQL 14+
- **AI:** OpenAI API (gpt-4o-mini)
- **Libraries:** requests, psycopg2, PyYAML, openai
- **Containerization:** Docker & Docker Compose

---

## 📄 License

This is an educational/personal project. Use at your own risk.

---

## 🤝 Contributing

This project follows strict architectural guidelines:
1. Each script must be idempotent
2. Clear separation between ingestion/normalization/insights
3. No predictions or financial advice
4. Type hints and docstrings required
5. Logging for all critical operations

See [CONTRIBUTING.md](docs/instructions/) for details.
