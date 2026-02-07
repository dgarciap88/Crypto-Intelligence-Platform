# Setup Guide - Crypto Intelligence Platform

## Prerequisites

- Python 3.11+
- PostgreSQL 14+
- Git

---

## Step-by-Step Setup

### 1. Clone and Navigate

```bash
cd Crypto-Intelligence-Platform
```

### 2. Create Virtual Environment

```bash
# Windows
python -m venv venv
.\venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Setup PostgreSQL Database

#### Option A: Local PostgreSQL

```bash
# Create database
createdb crypto_intel

# Create user (optional)
psql -c "CREATE USER cip_user WITH PASSWORD 'your_password';"
psql -c "GRANT ALL PRIVILEGES ON DATABASE crypto_intel TO cip_user;"

# Run schema
psql crypto_intel -f db/create_tables.sql
```

#### Option B: Docker PostgreSQL

```bash
# Run PostgreSQL in Docker
docker run -d \
  --name crypto-intel-db \
  -e POSTGRES_DB=crypto_intel \
  -e POSTGRES_USER=cip_user \
  -e POSTGRES_PASSWORD=your_password \
  -p 5432:5432 \
  postgres:14

# Wait a few seconds, then create tables
docker exec -i crypto-intel-db psql -U cip_user -d crypto_intel < db/create_tables.sql
```

### 5. Configure Environment

```bash
# Copy example
cp .env.example .env

# Edit .env with your values
# Windows: notepad .env
# Linux/Mac: nano .env
```

Required variables:
```bash
DATABASE_URL=postgresql://cip_user:your_password@localhost:5432/crypto_intel
GITHUB_TOKEN=ghp_your_github_token_here
OPENAI_API_KEY=sk-your_openai_key_here
```

To get tokens:
- **GitHub Token:** https://github.com/settings/tokens (needs repo:public_repo scope)
- **OpenAI Key:** https://platform.openai.com/api-keys

### 6. Test Connection

```bash
# Test database connection
python -c "import psycopg2; import os; psycopg2.connect(os.getenv('DATABASE_URL')).close(); print('✅ DB connected')"

# Load environment (if using .env file)
# Option 1: Use python-dotenv in scripts
# Option 2: Export manually
source .env  # Linux/Mac
# or
Get-Content .env | ForEach-Object { if($_ -match '^([^=]+)=(.*)$') { [System.Environment]::SetEnvironmentVariable($matches[1], $matches[2]) } }  # PowerShell
```

### 7. Run First Pipeline

```bash
# Complete pipeline (ingest → normalize → insights)
python run_pipeline.py --project-id arbitrum

# Or step-by-step:
python ingestion/github/ingest_github.py --project ./project.yaml
python ingestion/normalize.py --project-id arbitrum
python ingestion/generate_insights.py --project-id arbitrum --days 7
```

### 8. Query Results

```bash
# View insights
python query_insights.py --project-id arbitrum

# View insights + latest events
python query_insights.py --project-id arbitrum --latest-events 10
```

---

## Troubleshooting

### Database connection failed

```bash
# Check PostgreSQL is running
# Linux
sudo systemctl status postgresql

# Docker
docker ps | grep crypto-intel-db

# Test connection manually
psql -U cip_user -d crypto_intel -h localhost
```

### GitHub API rate limit

```bash
# Check your rate limit
curl -H "Authorization: token $GITHUB_TOKEN" https://api.github.com/rate_limit

# Without token: 60 requests/hour
# With token: 5000 requests/hour
```

### OpenAI API errors

```bash
# Test API key
python -c "import openai; client = openai.OpenAI(); print(client.models.list().data[0].id)"

# Common issues:
# - Invalid key: Check OPENAI_API_KEY format (starts with sk-)
# - Rate limit: Wait or upgrade plan
# - No credits: Add billing at platform.openai.com
```

### Import errors

```bash
# Reinstall dependencies
pip install --force-reinstall -r requirements.txt

# Check Python version
python --version  # Should be 3.11+
```

---

## Next Steps

1. **Customize project.yaml** - Add your own crypto projects
2. **Schedule pipeline** - Set up cron job or task scheduler
3. **Explore data** - Query insights and build dashboards
4. **Add sources** - Implement Twitter, Reddit, on-chain ingestion

---

## Quick Reference

```bash
# Full pipeline
python run_pipeline.py --project-id <project_id>

# Ingest only
python run_pipeline.py --project-id <project_id> --skip-normalize --skip-insights

# Query data
python query_insights.py --project-id <project_id> --latest-events 20

# Re-generate insights
python ingestion/generate_insights.py --project-id <project_id> --force
```

---

## Development

```bash
# Install dev dependencies (future)
# pip install -r requirements-dev.txt

# Run tests (future)
# pytest tests/

# Format code
# pip install black
# black ingestion/
```
