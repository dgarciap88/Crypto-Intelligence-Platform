# Crypto Intelligence Platform (CIP) - Arquitectura

## Objetivo
Una plataforma que detecta y explica cambios de interés y riesgo en proyectos crypto, usando datos on-chain, sociales y de desarrollo con IA que resume el “por qué”.  
**No predice precios ni da señales de trading.**

## Clientes objetivo
- Power users cripto
- DAOs pequeñas
- Fondos chicos / family offices
- Startups Web3

**Necesidad:** mucho dato, poco tiempo, cero ganas de leer manualmente.

## Tipos de señales
1. **Desarrollo**
   - GitHub commits, issues, releases
2. **Social / Narrativa**
   - X/Twitter, Reddit, Discord
   - Clasificación de eventos con IA
3. **On-chain**
   - Volumen, holders, movimientos grandes

## Flujo de datos
```text
project.yaml
    ↓
sources
    ↓
raw_events
    ↓
normalized_events
    ↓
signals
    ↓
ai_insights
