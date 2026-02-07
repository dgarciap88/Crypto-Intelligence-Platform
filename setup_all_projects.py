#!/usr/bin/env python3
"""
Setup all projects from projects.yaml into the database.

This script reads projects.yaml and:
1. Creates projects in the 'projects' table
2. Creates GitHub sources in the 'sources' table
3. Idempotent - can be run multiple times safely

Usage:
  python setup_all_projects.py [--projects-file projects.yaml]
"""

from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path
from typing import Dict, Any

import psycopg2
import yaml

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def pg_connect(dsn: str):
    """Connect to PostgreSQL database."""
    return psycopg2.connect(dsn)


def load_projects_config(file_path: str) -> list[Dict[str, Any]]:
    """Load projects configuration from YAML file."""
    with open(file_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    
    if not config or "projects" not in config:
        raise ValueError("Invalid projects.yaml format - missing 'projects' key")
    
    return config["projects"]


def add_project(
    conn,
    project_id: str,
    name: str,
    category: str | None = None,
    token_symbol: str | None = None,
    description: str | None = None
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
            logger.info("  ✓ Project '%s' already exists", project_id)
            return row[0]
        
        # Create new
        cur.execute(
            """
            INSERT INTO projects (project_id, name, category, token_symbol, description)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
            """,
            (project_id, name, category, token_symbol, description),
        )
        project_uuid = cur.fetchone()[0]
        conn.commit()
        
        logger.info("  ✅ Created project '%s'", project_id)
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
            logger.info("    ✓ Source '%s' already exists", reference)
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
        
        logger.info("    ✅ Added GitHub source: %s", reference)
        return source_uuid


def setup_project(conn, project_config: Dict[str, Any]) -> None:
    """Setup a single project with all its sources."""
    project_id = project_config["project_id"]
    name = project_config["name"]
    category = project_config.get("category")
    description = project_config.get("description")
    
    # Get token symbol if exists
    token_symbol = None
    if "token" in project_config and "symbol" in project_config["token"]:
        token_symbol = project_config["token"]["symbol"]
    
    logger.info("")
    logger.info("=" * 60)
    logger.info("Setting up: %s (%s)", name, project_id)
    logger.info("=" * 60)
    
    # Add project
    project_uuid = add_project(
        conn,
        project_id,
        name,
        category,
        token_symbol,
        description
    )
    
    # Add GitHub sources
    if "github" in project_config and "repositories" in project_config["github"]:
        logger.info("  GitHub repositories:")
        for repo in project_config["github"]["repositories"]:
            owner = repo["owner"]
            repo_name = repo["repo"]
            add_github_source(conn, project_uuid, owner, repo_name)
    
    # Future: Add Twitter sources
    # if "social" in project_config and "twitter" in project_config["social"]:
    #     logger.info("  Twitter handles: (not implemented yet)")
    #     for twitter in project_config["social"]["twitter"]:
    #         logger.info("    - @%s", twitter["handle"])
    
    # Future: Add Reddit sources
    # if "social" in project_config and "reddit" in project_config["social"]:
    #     logger.info("  Reddit subreddits: (not implemented yet)")
    #     for reddit in project_config["social"]["reddit"]:
    #         logger.info("    - r/%s", reddit["subreddit"])


def main(argv: list[str] | None = None) -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Setup all projects from projects.yaml")
    parser.add_argument(
        "--projects-file",
        default="projects.yaml",
        help="Path to projects.yaml file (default: projects.yaml)"
    )
    args = parser.parse_args(argv)

    # Check DATABASE_URL
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        logger.error("DATABASE_URL not set in environment")
        return 2

    # Check projects file exists
    projects_file = Path(args.projects_file)
    if not projects_file.exists():
        logger.error("Projects file not found: %s", projects_file)
        return 1

    # Load projects
    try:
        projects = load_projects_config(str(projects_file))
        logger.info("Loaded %d projects from %s", len(projects), projects_file)
    except Exception as e:
        logger.error("Error loading projects.yaml: %s", e)
        return 1

    # Connect to database
    conn = pg_connect(dsn)
    try:
        # Setup each project
        for project_config in projects:
            try:
                setup_project(conn, project_config)
            except Exception as e:
                logger.error("Error setting up project %s: %s", 
                           project_config.get("project_id", "unknown"), e)
                # Continue with next project
        
        logger.info("")
        logger.info("=" * 60)
        logger.info("✅ Setup complete! %d projects configured", len(projects))
        logger.info("=" * 60)
        logger.info("")
        logger.info("Next step:")
        logger.info("  python run_all_projects.py --days 7")
        logger.info("")
        
        return 0
        
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
