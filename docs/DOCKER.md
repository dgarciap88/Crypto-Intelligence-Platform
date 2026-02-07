# Docker Guide - Crypto Intelligence Platform

Guía completa para ejecutar CIP usando Docker.

## 🚀 Quick Start

### Opción 1: Docker Compose (Recomendado)

```bash
# 1. Configurar environment
cp .env.example .env
# Editar .env con tus valores

# 2. Iniciar todo (app + database)
docker-compose up -d

# 3. Ver logs
docker-compose logs -f

# 4. Verificar estado
docker-compose ps
```

### Opción 2: Docker Manual

```bash
# 1. Network
docker network create cip-network

# 2. PostgreSQL
docker run -d \
  --name cip-postgres \
  --network cip-network \
  -e POSTGRES_DB=crypto_intel \
  -e POSTGRES_USER=cip_user \
  -e POSTGRES_PASSWORD=your_password \
  -p 5432:5432 \
  -v cip-postgres-data:/var/lib/postgresql/data \
  postgres:14-alpine

# 3. Inicializar schema
docker exec -i cip-postgres psql -U cip_user -d crypto_intel < db/create_tables.sql

# 4. Build app
docker build -t cip-app .

# 5. Run app
docker run -d \
  --name cip-app \
  --network cip-network \
  -e DATABASE_URL=postgresql://cip_user:your_password@cip-postgres:5432/crypto_intel \
  -e GITHUB_TOKEN=your_token \
  -e OPENAI_API_KEY=your_key \
  -v $(pwd)/project.yaml:/app/project.yaml:ro \
  -v $(pwd)/logs:/app/logs \
  cip-app
```

---

## 📦 Arquitectura

```
┌─────────────────────────────────────────────┐
│         docker-compose.yml                  │
├─────────────────────────────────────────────┤
│                                             │
│  ┌──────────────┐      ┌──────────────┐   │
│  │  PostgreSQL  │◄─────┤   CIP App    │   │
│  │   (port      │      │  (Python)    │   │
│  │    5432)     │      │              │   │
│  └──────────────┘      └──────────────┘   │
│         │                                   │
│         ▼                                   │
│  ┌──────────────┐                          │
│  │   PgAdmin    │                          │
│  │  (port 5050) │                          │
│  │  [optional]  │                          │
│  └──────────────┘                          │
│                                             │
└─────────────────────────────────────────────┘
```

---

## 🔧 Configuración

### Variables de Entorno (.env)

```bash
# Database
POSTGRES_DB=crypto_intel
POSTGRES_USER=cip_user
POSTGRES_PASSWORD=secure_password_here
POSTGRES_PORT=5432

# GitHub API
GITHUB_TOKEN=ghp_your_token_here

# OpenAI API
OPENAI_API_KEY=sk-your_key_here

# PgAdmin (opcional)
PGADMIN_EMAIL=admin@cip.local
PGADMIN_PASSWORD=admin
PGADMIN_PORT=5050
```

### docker-compose.yml Profiles

```bash
# Solo app + database (default)
docker-compose up -d

# Con PgAdmin
docker-compose --profile admin up -d

# Ver servicios activos
docker-compose ps
```

---

## 🛠️ Comandos Útiles

### Gestión de Containers

```bash
# Iniciar
docker-compose up -d

# Detener
docker-compose down

# Detener y eliminar volúmenes (⚠️ elimina datos)
docker-compose down -v

# Reiniciar
docker-compose restart

# Reiniciar solo app
docker-compose restart app

# Ver estado
docker-compose ps

# Ver uso de recursos
docker stats
```

### Logs

```bash
# Todos los servicios
docker-compose logs -f

# Solo app
docker-compose logs -f app

# Solo postgres
docker-compose logs -f postgres

# Últimas 100 líneas
docker-compose logs --tail=100 app
```

### Ejecutar Comandos

```bash
# Shell en el container de app
docker-compose exec app bash

# Shell en PostgreSQL
docker-compose exec postgres psql -U cip_user -d crypto_intel

# Python REPL
docker-compose exec app python

# Ejecutar script específico
docker-compose exec app python ingestion/github/ingest_github.py --project project.yaml
```

### Build y Updates

```bash
# Rebuild después de cambios en código
docker-compose build

# Rebuild forzando sin cache
docker-compose build --no-cache

# Pull de imágenes base actualizadas
docker-compose pull

# Recrear containers
docker-compose up -d --force-recreate
```

---

## 📊 Operaciones Comunes

### Ejecutar Pipeline Completo

```bash
# Opción 1: Modificar command en docker-compose.yml
# Cambiar la línea command a:
# command: python run_pipeline.py --project-id arbitrum --days 7

# Opción 2: Ejecutar manualmente
docker-compose exec app python run_pipeline.py --project-id arbitrum --days 7
```

### Consultar Insights

```bash
docker-compose exec app python query_insights.py --project-id arbitrum --latest-events 10
```

### Normalizar Eventos

```bash
docker-compose exec app python ingestion/normalize.py --project-id arbitrum
```

### Generar Insights

```bash
docker-compose exec app python ingestion/generate_insights.py --project-id arbitrum --days 7 --force
```

---

## 💾 Gestión de Datos

### Backups

```bash
# Backup de PostgreSQL
docker-compose exec postgres pg_dump -U cip_user crypto_intel > backup_$(date +%Y%m%d).sql

# Backup comprimido
docker-compose exec postgres pg_dump -U cip_user crypto_intel | gzip > backup_$(date +%Y%m%d).sql.gz

# Backup de volúmenes
docker run --rm \
  -v crypto-intelligence-platform_postgres_data:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/postgres_volume_backup.tar.gz /data
```

### Restore

```bash
# Desde archivo SQL
cat backup_20260207.sql | docker-compose exec -T postgres psql -U cip_user -d crypto_intel

# Desde archivo comprimido
gunzip -c backup_20260207.sql.gz | docker-compose exec -T postgres psql -U cip_user -d crypto_intel
```

### Limpiar Base de Datos

```bash
# Conectar y eliminar datos
docker-compose exec postgres psql -U cip_user -d crypto_intel -c "
TRUNCATE TABLE ai_insights, normalized_events, raw_events, sources, projects CASCADE;
"
```

---

## 🔍 Debugging

### Health Checks

```bash
# Verificar health de containers
docker-compose ps

# Health check manual de PostgreSQL
docker-compose exec postgres pg_isready -U cip_user -d crypto_intel

# Health check de app
docker-compose exec app python -c "import psycopg2; import os; psycopg2.connect(os.getenv('DATABASE_URL')).close(); print('✅ DB connection OK')"
```

### Inspeccionar Containers

```bash
# Ver configuración de un container
docker inspect cip-app

# Ver variables de entorno
docker-compose exec app env

# Ver procesos corriendo
docker-compose exec app ps aux
```

### Network Issues

```bash
# Listar networks
docker network ls

# Inspeccionar network
docker network inspect crypto-intelligence-platform_cip-network

# Test conectividad
docker-compose exec app ping postgres
docker-compose exec app nc -zv postgres 5432
```

---

## 🔒 Seguridad

### Mejores Prácticas

1. **No commitear .env**
   ```bash
   # Asegurarse que .env está en .gitignore
   echo ".env" >> .gitignore
   ```

2. **Usar secrets en producción**
   ```yaml
   # docker-compose.yml
   services:
     app:
       secrets:
         - db_password
         - github_token
   secrets:
     db_password:
       file: ./secrets/db_password.txt
   ```

3. **Usuario no-root**
   - El Dockerfile ya crea y usa `appuser`

4. **Escanear vulnerabilidades**
   ```bash
   docker scan cip-app
   ```

---

## 📈 Performance

### Limitar Recursos

En `docker-compose.yml`:
```yaml
services:
  app:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          memory: 512M
```

### Optimizar Imágenes

```bash
# Ver tamaño de imágenes
docker images | grep cip

# Limpiar imágenes no usadas
docker image prune -a

# Multi-stage build ya implementado en Dockerfile
```

---

## 🐛 Troubleshooting

### Container no inicia

```bash
# Ver logs detallados
docker-compose logs app

# Ver últimos errores
docker-compose logs --tail=50 app | grep -i error
```

### Database connection failed

```bash
# Verificar que postgres está running
docker-compose ps postgres

# Test de conexión
docker-compose exec postgres psql -U cip_user -d crypto_intel -c "SELECT 1"

# Revisar DATABASE_URL
docker-compose exec app env | grep DATABASE_URL
```

### Out of disk space

```bash
# Ver uso de espacio
docker system df

# Limpiar todo lo no usado
docker system prune -a --volumes
```

### Permission denied

```bash
# Dar permisos al directorio logs
mkdir -p logs
chmod 777 logs

# O cambiar owner
sudo chown -R $USER:$USER logs
```

---

## 🚀 Deployment en Producción

### Docker Swarm

```bash
# Inicializar swarm
docker swarm init

# Deploy stack
docker stack deploy -c docker-compose.yml cip

# Ver servicios
docker service ls

# Escalar app
docker service scale cip_app=3
```

### Kubernetes

Ver `/kubernetes` en el repositorio Support para manifiestos completos.

---

## 📚 Referencias

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Reference](https://docs.docker.com/compose/compose-file/)
- [PostgreSQL Docker Image](https://hub.docker.com/_/postgres)
- [Python Docker Image](https://hub.docker.com/_/python)
