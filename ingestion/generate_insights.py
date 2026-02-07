"""Generate AI insights from normalized events.

This script reads normalized events and generates AI-powered summaries and analysis.
It uses OpenAI API (or compatible APIs) to generate insights.

Usage:
  python ingestion/generate_insights.py --project-id arbitrum [--days 7]

Environment variables:
  DATABASE_URL: postgres connection string
  OPENAI_API_KEY: OpenAI API key (or compatible API)
  OPENAI_API_BASE: Optional base URL for API (default: https://api.openai.com/v1)

This script generates weekly summaries of development activity.
"""

from __future__ import annotations

import argparse
import os
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta, timezone

import psycopg2
from psycopg2.extras import Json, RealDictCursor

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logging.warning("openai package not installed. Install with: pip install openai")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def pg_connect(dsn: str):
    """Connect to PostgreSQL database."""
    return psycopg2.connect(dsn)


def get_project_uuid(conn, project_id: str) -> Optional[str]:
    """Get project UUID from project_id."""
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM projects WHERE project_id = %s", (project_id,))
        row = cur.fetchone()
        return row[0] if row else None


def fetch_recent_events(conn, project_uuid: str, days: int) -> List[Dict[str, Any]]:
    """Fetch normalized events from the last N days."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT * 
            FROM normalized_events
            WHERE project_id = %s 
              AND event_timestamp >= %s
            ORDER BY event_timestamp DESC
            """,
            (project_uuid, cutoff),
        )
        return [dict(row) for row in cur.fetchall()]


def check_insight_exists(conn, project_uuid: str, insight_type: str, days: int) -> bool:
    """Check if an insight of this type was generated recently."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=12)  # Don't regenerate if generated in last 12h
    
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id FROM ai_insights
            WHERE project_id = %s 
              AND insight_type = %s
              AND created_at >= %s
            LIMIT 1
            """,
            (project_uuid, insight_type, cutoff),
        )
        return cur.fetchone() is not None


def format_events_for_prompt(events: List[Dict[str, Any]]) -> str:
    """Format events into a readable text for the LLM."""
    if not events:
        return "No events found in this period."
    
    lines = []
    lines.append(f"Total events: {len(events)}\n")
    
    # Group by entity_type
    by_type: Dict[str, List[Dict[str, Any]]] = {}
    for event in events:
        entity_type = event.get("entity_type", "unknown")
        by_type.setdefault(entity_type, []).append(event)
    
    for entity_type, type_events in by_type.items():
        lines.append(f"\n## {entity_type.upper()}S ({len(type_events)})")
        for event in type_events[:20]:  # Limit to first 20 per type
            ts = event.get("event_timestamp", "")
            title = event.get("title", "")
            description = event.get("description", "")[:200]
            lines.append(f"- [{ts}] {title}")
            if description:
                lines.append(f"  {description}")
    
    return "\n".join(lines)


def generate_insight_with_openai(
    api_key: str, 
    project_id: str, 
    events_text: str,
    api_base: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate insight using OpenAI API in both Spanish and English.
    
    Returns dict with: title, content (Spanish), content_translations (dict with 'en' and 'es'), confidence
    """
    if not OPENAI_AVAILABLE:
        raise RuntimeError("openai package is not installed")
    
    client = openai.OpenAI(api_key=api_key, base_url=api_base)
    
    # Generate Spanish version
    prompt_es = f"""Eres un analista de IA para proyectos crypto/blockchain. 
Analiza la siguiente actividad de desarrollo del proyecto "{project_id}" y proporciona:
1. Un resumen breve (2-3 frases) de los desarrollos clave
2. Patrones o tendencias notables
3. Áreas de enfoque (¿en qué están trabajando?)

NO DEBES:
- Hacer predicciones de precio
- Dar consejos financieros
- Especular más allá de lo que muestran los datos

Datos de eventos:
{events_text}

Proporciona un análisis claro y factual en español."""

    # Generate English version
    prompt_en = f"""You are an AI analyst for crypto/blockchain projects. 
Analyze the following development activity for the project "{project_id}" and provide:
1. A brief summary (2-3 sentences) of key developments
2. Notable patterns or trends
3. Areas of focus (what are they working on?)

DO NOT:
- Make price predictions
- Give financial advice
- Speculate beyond what the data shows

Events data:
{events_text}

Provide a clear, factual analysis in English."""

    try:
        # Generate Spanish content
        response_es = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Eres un analista técnico para proyectos blockchain. Sé factual y conciso. Responde siempre en español."},
                {"role": "user", "content": prompt_es}
            ],
            temperature=0.3,
            max_tokens=500
        )
        content_es = response_es.choices[0].message.content or ""
        
        # Generate English content
        response_en = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a technical analyst for blockchain projects. Be factual and concise. Always respond in English."},
                {"role": "user", "content": prompt_en}
            ],
            temperature=0.3,
            max_tokens=500
        )
        content_en = response_en.choices[0].message.content or ""
        
        return {
            "title": f"Development Summary - {project_id}",
            "content": content_es,  # Default to Spanish
            "content_translations": {
                "es": content_es,
                "en": content_en
            },
            "confidence": 0.8,
        }
    
    except Exception as e:
        logger.exception("Error calling OpenAI API: %s", e)
        raise


def insert_insight(
    conn, 
    project_uuid: str, 
    insight_type: str,
    title: str,
    content: str,
    confidence: float,
    source_event_ids: List[str],
    metadata: Dict[str, Any],
    content_translations: Optional[Dict[str, str]] = None
) -> None:
    """Insert an AI insight into the database."""
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO ai_insights 
            (project_id, insight_type, title, content, confidence, source_event_ids, metadata, content_translations)
            VALUES (%s, %s, %s, %s, %s, %s::uuid[], %s, %s)
            """,
            (
                project_uuid,
                insight_type,
                title,
                content,
                confidence,
                source_event_ids,
                Json(metadata),
                Json(content_translations or {}),
            ),
        )
    conn.commit()


def main(argv: Optional[List[str]] = None) -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Generate AI insights from events")
    parser.add_argument("--project-id", required=True, help="Project ID to analyze")
    parser.add_argument("--days", type=int, default=7, help="Number of days to analyze")
    parser.add_argument("--force", action="store_true", help="Force regenerate even if recent insight exists")
    args = parser.parse_args(argv)

    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        logger.error("DATABASE_URL not set in environment")
        return 2
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.error("OPENAI_API_KEY not set in environment")
        return 2
    
    api_base = os.getenv("OPENAI_API_BASE")

    conn = pg_connect(dsn)
    try:
        project_uuid = get_project_uuid(conn, args.project_id)
        if not project_uuid:
            logger.error("Project not found: %s", args.project_id)
            return 2

        insight_type = "summary"
        
        if not args.force and check_insight_exists(conn, project_uuid, insight_type, args.days):
            logger.info("Recent insight already exists. Use --force to regenerate.")
            return 0

        logger.info("Fetching events for project: %s (last %d days)", args.project_id, args.days)
        events = fetch_recent_events(conn, project_uuid, args.days)
        
        if not events:
            logger.warning("No events found for the specified period")
            return 0
        
        logger.info("Found %d events", len(events))
        
        events_text = format_events_for_prompt(events)
        logger.info("Generating AI insight...")
        
        insight = generate_insight_with_openai(api_key, args.project_id, events_text, api_base)
        
        source_event_ids = [str(e["id"]) for e in events[:50]]  # Reference up to 50 events
        metadata = {
            "days_analyzed": args.days,
            "event_count": len(events),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        
        insert_insight(
            conn,
            project_uuid,
            insight_type,
            insight["title"],
            insight["content"],
            insight["confidence"],
            source_event_ids,
            metadata,
            insight.get("content_translations"),
        )
        
        logger.info("✅ Insight generated successfully")
        logger.info("Title: %s", insight["title"])
        logger.info("Content:\n%s", insight["content"])
        
        return 0
        
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
