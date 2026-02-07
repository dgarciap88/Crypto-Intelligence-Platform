# ⚠️ Database Schema Moved

**Los schemas de la base de datos se han movido al proyecto Support.**

## Nueva Ubicación

```
Crypto-Intelligence-Platform-Support/db/create_tables.sql
```

## Razón del Cambio

El schema es compartido por múltiples servicios:
- **Platform** (ingestion pipeline)
- **API** (backend REST)
- **Web** (frontend)

Para evitar inconsistencias y facilitar el mantenimiento, los schemas ahora están centralizados en el repositorio de infraestructura compartida.

## Cómo Usar

### Inicializar Schema

```bash
# Desde el directorio Support
cd ../Crypto-Intelligence-Platform-Support
Get-Content db/create_tables.sql | docker exec -i cip-postgres psql -U crypto_user -d crypto_intel
```

### Modificar Schema

1. Edita `Support/db/create_tables.sql`
2. Actualiza modelos en:
   - API: `Crypto-Intelligence-API/app/models.py`
   - Frontend: `Crypto-Intelligence-Web/src/types/index.ts`
3. Documenta cambios en `Support/db/README.md`

## Documentación

Ver:
- `../Crypto-Intelligence-Platform-Support/db/README.md` - Documentación completa del schema
- `../Crypto-Intelligence-Platform-Support/README.md` - Setup y deployment
