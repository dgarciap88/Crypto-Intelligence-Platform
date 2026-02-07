"""
Query insights and events from the database.

This is a utility script for exploring the data.

Usage:
  python query_insights.py --project-id arbitrum
  python query_insights.py --project-id arbitrum --latest-events 10
"""

from __future__ import annotations

import argparse
import os
import logging
from typing import List, Dict, Any

import psycopg2
from psycopg2.extras import RealDictCursor

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def pg_connect(dsn: str):
    """Connect to PostgreSQL database."""
    return psycopg2.connect(dsn)


def get_latest_insights(conn, project_id: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Get the latest AI insights for a project."""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT 
                ai.id,
                ai.insight_type,
                ai.title,
                ai.content,
                ai.confidence,
                ai.created_at,
                p.name as project_name,
                jsonb_array_length(COALESCE(ai.source_event_ids, '[]'::jsonb)) as event_count
            FROM ai_insights ai
            JOIN projects p ON p.id = ai.project_id
            WHERE p.project_id = %s
            ORDER BY ai.created_at DESC
            LIMIT %s
            """,
            (project_id, limit),
        )
        return [dict(row) for row in cur.fetchall()]


def get_latest_events(conn, project_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Get the latest normalized events for a project."""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT 
                ne.id,
                ne.entity_type,
                ne.entity_id,
                ne.title,
                ne.description,
                ne.event_timestamp,
                s.source_type,
                s.reference
            FROM normalized_events ne
            JOIN sources s ON s.id = ne.source_id
            JOIN projects p ON p.id = ne.project_id
            WHERE p.project_id = %s
            ORDER BY ne.event_timestamp DESC
            LIMIT %s
            """,
            (project_id, limit),
        )
        return [dict(row) for row in cur.fetchall()]


def get_stats(conn, project_id: str) -> Dict[str, Any]:
    """Get statistics about a project's data."""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        # Count events by type
        cur.execute(
            """
            SELECT 
                COUNT(*) as total_raw_events,
                COUNT(DISTINCT source_id) as source_count
            FROM raw_events re
            JOIN projects p ON p.id = re.project_id
            WHERE p.project_id = %s
            """,
            (project_id,),
        )
        raw = dict(cur.fetchone() or {})
        
        cur.execute(
            """
            SELECT COUNT(*) as total_normalized_events
            FROM normalized_events ne
            JOIN projects p ON p.id = ne.project_id
            WHERE p.project_id = %s
            """,
            (project_id,),
        )
        normalized = dict(cur.fetchone() or {})
        
        cur.execute(
            """
            SELECT COUNT(*) as total_insights
            FROM ai_insights ai
            JOIN projects p ON p.id = ai.project_id
            WHERE p.project_id = %s
            """,
            (project_id,),
        )
        insights = dict(cur.fetchone() or {})
        
        return {**raw, **normalized, **insights}


def print_insights(insights: List[Dict[str, Any]]) -> None:
    """Pretty print insights."""
    if not insights:
        print("No insights found.")
        return
    
    print("\n" + "=" * 80)
    print("AI INSIGHTS")
    print("=" * 80)
    
    for i, insight in enumerate(insights, 1):
        print(f"\n[{i}] {insight['title']}")
        print(f"    Type: {insight['insight_type']}")
        print(f"    Created: {insight['created_at']}")
        print(f"    Confidence: {insight.get('confidence', 'N/A')}")
        print(f"    Based on {insight.get('event_count', 0)} events")
        print(f"\n{insight['content']}")
        print("-" * 80)


def print_events(events: List[Dict[str, Any]]) -> None:
    """Pretty print events."""
    if not events:
        print("No events found.")
        return
    
    print("\n" + "=" * 80)
    print("LATEST EVENTS")
    print("=" * 80)
    
    for i, event in enumerate(events, 1):
        print(f"\n[{i}] {event['entity_type'].upper()}: {event['title']}")
        print(f"    Source: {event['source_type']} ({event['reference']})")
        print(f"    Timestamp: {event['event_timestamp']}")
        if event.get('description'):
            desc = event['description'][:150]
            print(f"    {desc}{'...' if len(event['description']) > 150 else ''}")
        print("-" * 80)


def main(argv: List[str] | None = None) -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Query insights and events")
    parser.add_argument("--project-id", required=True, help="Project ID to query")
    parser.add_argument("--latest-events", type=int, help="Show N latest events")
    parser.add_argument("--latest-insights", type=int, default=3, help="Show N latest insights")
    args = parser.parse_args(argv)

    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        logger.error("DATABASE_URL not set in environment")
        return 2

    conn = pg_connect(dsn)
    try:
        print(f"\n🔍 Querying project: {args.project_id}")
        
        # Get stats
        stats = get_stats(conn, args.project_id)
        print("\n📊 Statistics:")
        print(f"  - Raw events: {stats.get('total_raw_events', 0)}")
        print(f"  - Normalized events: {stats.get('total_normalized_events', 0)}")
        print(f"  - AI insights: {stats.get('total_insights', 0)}")
        print(f"  - Data sources: {stats.get('source_count', 0)}")
        
        # Get and print insights
        insights = get_latest_insights(conn, args.project_id, args.latest_insights)
        print_insights(insights)
        
        # Get and print events if requested
        if args.latest_events:
            events = get_latest_events(conn, args.project_id, args.latest_events)
            print_events(events)
        
        return 0
        
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
