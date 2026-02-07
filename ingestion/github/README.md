# GitHub ingestion

Uso básico:

- Configura las variables de entorno:

```
export DATABASE_URL=postgresql://user:pass@localhost:5432/cip
export GITHUB_TOKEN=ghp_...
```

- Ejecuta el script indicando el `project.yaml` si no está en la ruta por defecto:

```
python -m ingestion.github.ingest_github --project ./project.yaml
```

El script: 1) crea/obtiene `projects` y `sources`, 2) consulta commits y releases, 3) inserta eventos en `raw_events` de forma idempotente.
