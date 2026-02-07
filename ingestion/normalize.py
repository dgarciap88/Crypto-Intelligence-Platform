"""Normalize raw events into structured normalized_events table.

This script reads raw_events from the database and transforms them into a
normalized structure that's easier to query and analyze.

Usage:
  python ingestion/normalize.py --project-id arbitrum [--batch-size 100]

Environment variables:
  DATABASE_URL: postgres connection string

This script is idempotent: it will skip events that are already normalized.
"""

from __future__ import annotations

import argparse
import os
import logging
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

import psycopg2
from psycopg2.extras import Json, RealDictCursor

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


def fetch_raw_events_to_normalize(conn, project_uuid: str, batch_size: int) -> List[Dict[str, Any]]:
    """Fetch raw events that haven't been normalized yet."""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT re.* 
            FROM raw_events re
            LEFT JOIN normalized_events ne ON ne.raw_event_id = re.id
            WHERE re.project_id = %s AND ne.id IS NULL
            ORDER BY re.event_timestamp DESC
            LIMIT %s
            """,
            (project_uuid, batch_size),
        )
        return [dict(row) for row in cur.fetchall()]


def normalize_github_commit(raw_event: Dict[str, Any]) -> Tuple[str, str, str, str, Dict[str, Any]]:
    """
    Extract normalized fields from a github_commit raw event.
    
    Returns: (entity_type, entity_id, title, description, metadata)
    """
    payload = raw_event["payload"]
    sha = payload.get("sha", "")
    message = payload.get("message", "")
    author = payload.get("author", {}) or {}
    author_name = author.get("name", "unknown")
    
    # Split commit message: first line = title, rest = description
    lines = message.split("\n", 1)
    title = lines[0][:200] if lines else "Commit"
    description = lines[1].strip() if len(lines) > 1 else ""
    
    metadata = {
        "sha": sha,
        "author_name": author_name,
        "author_email": author.get("email"),
    }
    
    return ("commit", sha, title, description, metadata)


def normalize_github_release(raw_event: Dict[str, Any]) -> Tuple[str, str, str, str, Dict[str, Any]]:
    """
    Extract normalized fields from a github_release raw event.
    
    Returns: (entity_type, entity_id, title, description, metadata)
    """
    payload = raw_event["payload"]
    release_id = payload.get("unique_id", "")
    tag_name = payload.get("tag_name", "")
    name = payload.get("name", tag_name)
    raw_data = payload.get("raw", {})
    body = raw_data.get("body", "")
    
    title = f"Release {name or tag_name}"
    description = body[:1000] if body else ""
    
    metadata = {
        "tag_name": tag_name,
        "release_id": release_id,
        "draft": raw_data.get("draft", False),
        "prerelease": raw_data.get("prerelease", False),
    }
    
    return ("release", release_id, title, description, metadata)


def normalize_event(raw_event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Normalize a single raw event into normalized structure.
    
    Returns a dict with keys: entity_type, entity_id, title, description, metadata
    Or None if the event type is not yet supported.
    """
    event_type = raw_event["event_type"]
    
    try:
        if event_type == "github_commit":
            entity_type, entity_id, title, description, metadata = normalize_github_commit(raw_event)
        elif event_type == "github_release":
            entity_type, entity_id, title, description, metadata = normalize_github_release(raw_event)
        else:
            logger.warning("Unknown event_type: %s", event_type)
            return None
        
        return {
            "project_id": raw_event["project_id"],
            "source_id": raw_event["source_id"],
            "raw_event_id": raw_event["id"],
            "event_type": event_type,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "title": title,
            "description": description,
            "metadata": metadata,
            "event_timestamp": raw_event["event_timestamp"],
        }
    except Exception as e:
        logger.exception("Error normalizing event %s: %s", raw_event.get("id"), e)
        return None


def insert_normalized_event(conn, normalized: Dict[str, Any]) -> None:
    """Insert a normalized event into the database."""
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO normalized_events 
            (project_id, source_id, raw_event_id, event_type, entity_type, entity_id, 
             title, description, metadata, event_timestamp)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (raw_event_id) DO NOTHING
            """,
            (
                normalized["project_id"],
                normalized["source_id"],
                normalized["raw_event_id"],
                normalized["event_type"],
                normalized["entity_type"],
                normalized["entity_id"],
                normalized["title"],
                normalized["description"],
                Json(normalized["metadata"]),
                normalized["event_timestamp"],
            ),
        )
    conn.commit()


def main(argv: Optional[List[str]] = None) -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Normalize raw events")
    parser.add_argument("--project-id", required=True, help="Project ID to normalize")
    parser.add_argument("--batch-size", type=int, default=100, help="Number of events to process per batch")
    args = parser.parse_args(argv)

    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        logger.error("DATABASE_URL not set in environment")
        return 2

    conn = pg_connect(dsn)
    try:
        project_uuid = get_project_uuid(conn, args.project_id)
        if not project_uuid:
            logger.error("Project not found: %s", args.project_id)
            return 2

        logger.info("Normalizing events for project: %s", args.project_id)
        
        total_normalized = 0
        while True:
            raw_events = fetch_raw_events_to_normalize(conn, project_uuid, args.batch_size)
            if not raw_events:
                logger.info("No more events to normalize")
                break
            
            logger.info("Processing batch of %d raw events", len(raw_events))
            
            for raw_event in raw_events:
                normalized = normalize_event(raw_event)
                if normalized:
                    insert_normalized_event(conn, normalized)
                    total_normalized += 1
            
            logger.info("Normalized %d events so far", total_normalized)
        
        logger.info("✅ Normalization complete. Total: %d events", total_normalized)
        return 0
        
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
