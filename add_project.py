"""
Helper script to add a new project to the database programmatically.

Usage:
  python add_project.py --project-id uniswap --name Uniswap --category defi --token UNI
"""

from __future__ import annotations

import argparse
import os
import logging
from typing import Optional

import psycopg2

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def pg_connect(dsn: str):
    """Connect to PostgreSQL database."""
    return psycopg2.connect(dsn)


def add_project(
    conn,
    project_id: str,
    name: str,
    category: Optional[str] = None,
    token_symbol: Optional[str] = None
) -> str:
    """
    Add a project to the database.
    
    Returns the UUID of the created/existing project.
    """
    with conn.cursor() as cur:
        # Check if exists
        cur.execute("SELECT id FROM projects WHERE project_id = %s", (project_id,))
        row = cur.fetchone()
        
        if row:
            logger.info("Project '%s' already exists", project_id)
            return row[0]
        
        # Create new
        cur.execute(
            """
            INSERT INTO projects (project_id, name, category, token_symbol)
            VALUES (%s, %s, %s, %s)
            RETURNING id
            """,
            (project_id, name, category, token_symbol),
        )
        project_uuid = cur.fetchone()[0]
        conn.commit()
        
        logger.info("✅ Created project '%s' with UUID: %s", project_id, project_uuid)
        return project_uuid


def add_github_source(
    conn,
    project_uuid: str,
    owner: str,
    repo: str
) -> str:
    """
    Add a GitHub repository as a source.
    
    Returns the UUID of the created/existing source.
    """
    reference = f"{owner}/{repo}"
    
    with conn.cursor() as cur:
        # Check if exists
        cur.execute(
            "SELECT id FROM sources WHERE source_type = 'github' AND reference = %s",
            (reference,)
        )
        row = cur.fetchone()
        
        if row:
            logger.info("Source '%s' already exists", reference)
            return row[0]
        
        # Create new
        cur.execute(
            """
            INSERT INTO sources (project_id, source_type, reference, metadata)
            VALUES (%s, 'github', %s, %s)
            RETURNING id
            """,
            (project_uuid, reference, f'{{"owner": "{owner}", "repo": "{repo}"}}'),
        )
        source_uuid = cur.fetchone()[0]
        conn.commit()
        
        logger.info("✅ Added GitHub source: %s", reference)
        return source_uuid


def main(argv: list[str] | None = None) -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Add a new project to CIP")
    parser.add_argument("--project-id", required=True, help="Unique project identifier")
    parser.add_argument("--name", required=True, help="Project display name")
    parser.add_argument("--category", help="Project category (e.g., defi, layer2)")
    parser.add_argument("--token", help="Token symbol")
    parser.add_argument("--github-repos", nargs="+", help="GitHub repos in format 'owner/repo'")
    args = parser.parse_args(argv)

    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        logger.error("DATABASE_URL not set in environment")
        return 2

    conn = pg_connect(dsn)
    try:
        # Add project
        project_uuid = add_project(
            conn,
            args.project_id,
            args.name,
            args.category,
            args.token
        )
        
        # Add GitHub repos if provided
        if args.github_repos:
            for repo in args.github_repos:
                if "/" not in repo:
                    logger.warning("Invalid repo format '%s', expected 'owner/repo'", repo)
                    continue
                
                owner, repo_name = repo.split("/", 1)
                add_github_source(conn, project_uuid, owner, repo_name)
        
        logger.info("=" * 60)
        logger.info("✅ Project setup complete!")
        logger.info("=" * 60)
        logger.info("")
        logger.info("Next steps:")
        logger.info("  1. Run ingestion:")
        logger.info(f"     python ingestion/github/ingest_github.py --project <path_to_yaml>")
        logger.info("")
        logger.info("  2. Or create a project.yaml:")
        print(f"""
---
project_id: {args.project_id}
name: {args.name}
category: {args.category or 'general'}
{f'token:\\n  symbol: {args.token}' if args.token else ''}
github:
  repositories:
""")
        if args.github_repos:
            for repo in args.github_repos:
                if "/" in repo:
                    owner, repo_name = repo.split("/", 1)
                    print(f"    - owner: {owner}")
                    print(f"      repo: {repo_name}")
        
        return 0
        
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
