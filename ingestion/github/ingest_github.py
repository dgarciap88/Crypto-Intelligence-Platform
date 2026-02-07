"""Idempotent GitHub ingestion for CIP.

Reads a `project.yaml` following docs/project-schema.md, fetches commits and releases
for listed repositories and inserts normalized events into `raw_events`.

Usage:
  python ingestion/github/ingest_github.py --project ./project.yaml

Environment variables:
  DATABASE_URL: postgres connection string
  GITHUB_TOKEN: optional GitHub token to increase rate limits

This script is intentionally simple and synchronous for clarity. It's written to be
clear, idempotent, and easy to test.
"""

from __future__ import annotations

import argparse
import os
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import requests
import yaml
import psycopg2
from psycopg2.extras import Json

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


GITHUB_API = "https://api.github.com"


def load_project_yaml(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def pg_connect(dsn: str):
    return psycopg2.connect(dsn)


def ensure_project(conn, project_id: str, name: str, category: Optional[str], token_symbol: Optional[str]):
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM projects WHERE project_id = %s", (project_id,))
        row = cur.fetchone()
        if row:
            return row[0]
        cur.execute(
            "INSERT INTO projects (project_id, name, category, token_symbol) VALUES (%s,%s,%s,%s) RETURNING id",
            (project_id, name, category, token_symbol),
        )
        proj_id = cur.fetchone()[0]
        conn.commit()
        return proj_id


def ensure_source(conn, project_db_id, source_type: str, reference: str, metadata: Dict[str, Any]):
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id FROM sources WHERE source_type=%s AND reference=%s",
            (source_type, reference),
        )
        row = cur.fetchone()
        if row:
            return row[0]
        cur.execute(
            "INSERT INTO sources (project_id, source_type, reference, metadata) VALUES (%s,%s,%s,%s) RETURNING id",
            (project_db_id, source_type, reference, Json(metadata)),
        )
        src_id = cur.fetchone()[0]
        conn.commit()
        return src_id


def already_exists_event(conn, source_id, event_type: str, unique_id_key: str, unique_id_value: str) -> bool:
    with conn.cursor() as cur:
        # payload->>unique_id_key = unique_id_value
        cur.execute(
            "SELECT id FROM raw_events WHERE source_id=%s AND event_type=%s AND payload->>%s = %s",
            (source_id, event_type, unique_id_key, unique_id_value),
        )
        return cur.fetchone() is not None


def insert_raw_event(conn, project_db_id, source_id, event_type: str, payload: Dict[str, Any], event_ts: str):
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO raw_events (project_id, source_id, event_type, payload, event_timestamp) VALUES (%s,%s,%s,%s,%s)",
            (project_db_id, source_id, event_type, Json(payload), event_ts),
        )
        conn.commit()


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def fetch_commits(owner: str, repo: str, token: Optional[str]) -> List[Dict[str, Any]]:
    url = f"{GITHUB_API}/repos/{owner}/{repo}/commits"
    headers = {"Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"token {token}"
    resp = requests.get(url, headers=headers, params={"per_page": 100})
    resp.raise_for_status()
    return resp.json()


def fetch_releases(owner: str, repo: str, token: Optional[str]) -> List[Dict[str, Any]]:
    url = f"{GITHUB_API}/repos/{owner}/{repo}/releases"
    headers = {"Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"token {token}"
    resp = requests.get(url, headers=headers, params={"per_page": 100})
    resp.raise_for_status()
    return resp.json()


def process_repo(conn, project_db_id, owner: str, repo: str, token: Optional[str]):
    reference = f"{owner}/{repo}"
    src_id = ensure_source(conn, project_db_id, "github", reference, {"owner": owner, "repo": repo})

    # Commits
    commits = fetch_commits(owner, repo, token)
    logger.info("Fetched %d commits for %s", len(commits), reference)
    for c in commits:
        sha = c.get("sha")
        if not sha:
            continue
        payload = {
            "unique_id": sha,
            "sha": sha,
            "message": c.get("commit", {}).get("message"),
            "author": c.get("commit", {}).get("author"),
            "raw": c,
        }
        if already_exists_event(conn, src_id, "github_commit", "unique_id", sha):
            continue
        commit_obj = c.get("commit", {}) or {}
        event_ts = (
            (commit_obj.get("author") or {}).get("date")
            or (commit_obj.get("committer") or {}).get("date")
            or now_iso()
        )
        insert_raw_event(conn, project_db_id, src_id, "github_commit", payload, event_ts)

    # Releases
    releases = fetch_releases(owner, repo, token)
    logger.info("Fetched %d releases for %s", len(releases), reference)
    for r in releases:
        rid = str(r.get("id"))
        payload = {
            "unique_id": rid,
            "tag_name": r.get("tag_name"),
            "name": r.get("name"),
            "raw": r,
        }
        if already_exists_event(conn, src_id, "github_release", "unique_id", rid):
            continue
        # published_at can be null (draft releases). fall back to created_at, then now.
        event_ts = r.get("published_at") or r.get("created_at") or now_iso()
        insert_raw_event(conn, project_db_id, src_id, "github_release", payload, event_ts)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=False, default="project.yaml", help="Path to project.yaml")
    args = parser.parse_args(argv)

    project_path = args.project
    if not os.path.exists(project_path):
        logger.error("project.yaml not found at %s", project_path)
        return 2

    cfg = load_project_yaml(project_path)
    project_id = cfg.get("project_id")
    name = cfg.get("name")
    if not project_id or not name:
        logger.error("project.yaml must define project_id and name")
        return 2

    category = cfg.get("category")
    token_symbol = cfg.get("token", {}).get("symbol") if cfg.get("token") else None

    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        logger.error("DATABASE_URL not set in environment")
        return 2

    gh_token = os.getenv("GITHUB_TOKEN")

    conn = pg_connect(dsn)
    try:
        project_db_id = ensure_project(conn, project_id, name, category, token_symbol)

        # Process listed github repos
        github_cfg = cfg.get("github", {})
        repos = github_cfg.get("repositories", [])
        for r in repos:
            owner = r.get("owner")
            repo = r.get("repo")
            if not owner or not repo:
                continue
            logger.info("Processing %s/%s", owner, repo)
            try:
                process_repo(conn, project_db_id, owner, repo, gh_token)
            except Exception:
                logger.exception("Error processing repo %s/%s", owner, repo)
    finally:
        conn.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
