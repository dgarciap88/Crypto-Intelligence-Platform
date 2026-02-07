#!/usr/bin/env python3
"""
Run the complete CIP pipeline for a project.

This script orchestrates the full data pipeline:
1. Ingest raw data from sources
2. Normalize events
3. Generate AI insights

Usage:
  python run_pipeline.py --project-id arbitrum [--days 7] [--skip-ingest]
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

# Add ingestion directory to path
sys.path.insert(0, str(Path(__file__).parent / "ingestion"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def check_env_vars() -> bool:
    """Check that required environment variables are set."""
    required = ["DATABASE_URL"]
    missing = [var for var in required if not os.getenv(var)]
    
    if missing:
        logger.error("Missing required environment variables: %s", ", ".join(missing))
        return False
    
    # Optional but recommended
    if not os.getenv("GITHUB_TOKEN"):
        logger.warning("GITHUB_TOKEN not set - GitHub API rate limits will be lower")
    
    if not os.getenv("OPENAI_API_KEY"):
        logger.warning("OPENAI_API_KEY not set - insights generation will fail")
    
    return True


def run_stage(stage_name: str, module_name: str, args: list[str]) -> int:
    """Run a pipeline stage by importing and executing its main function."""
    logger.info("=" * 60)
    logger.info("STAGE: %s", stage_name)
    logger.info("=" * 60)
    
    try:
        if module_name == "github.ingest_github":
            from github import ingest_github
            return ingest_github.main(args)
        elif module_name == "normalize":
            import normalize
            return normalize.main(args)
        elif module_name == "generate_insights":
            import generate_insights
            return generate_insights.main(args)
        else:
            logger.error("Unknown module: %s", module_name)
            return 1
    except Exception as e:
        logger.exception("Error in stage %s: %s", stage_name, e)
        return 1


def main(argv: list[str] | None = None) -> int:
    """Main pipeline orchestrator."""
    parser = argparse.ArgumentParser(description="Run complete CIP pipeline")
    parser.add_argument("--project-id", required=True, help="Project ID to process")
    parser.add_argument("--project-yaml", default="project.yaml", help="Path to project.yaml")
    parser.add_argument("--days", type=int, default=7, help="Days of history for insights")
    parser.add_argument("--skip-ingest", action="store_true", help="Skip ingestion (use existing data)")
    parser.add_argument("--skip-normalize", action="store_true", help="Skip normalization")
    parser.add_argument("--skip-insights", action="store_true", help="Skip insights generation")
    args = parser.parse_args(argv)
    
    logger.info("🚀 Starting CIP Pipeline")
    logger.info("Project: %s", args.project_id)
    
    # Check environment
    if not check_env_vars():
        return 2
    
    # Stage 1: Ingest
    if not args.skip_ingest:
        if not os.path.exists(args.project_yaml):
            logger.error("Project YAML not found: %s", args.project_yaml)
            return 2
        
        ret = run_stage(
            "1. GitHub Ingestion",
            "github.ingest_github",
            ["--project", args.project_yaml]
        )
        if ret != 0:
            logger.error("Ingestion failed")
            return ret
    else:
        logger.info("⏭️  Skipping ingestion")
    
    # Stage 2: Normalize
    if not args.skip_normalize:
        ret = run_stage(
            "2. Event Normalization",
            "normalize",
            ["--project-id", args.project_id, "--batch-size", "100"]
        )
        if ret != 0:
            logger.error("Normalization failed")
            return ret
    else:
        logger.info("⏭️  Skipping normalization")
    
    # Stage 3: Insights
    if not args.skip_insights:
        if not os.getenv("OPENAI_API_KEY"):
            logger.warning("⚠️  OPENAI_API_KEY not set, skipping insights")
        else:
            ret = run_stage(
                "3. AI Insights Generation",
                "generate_insights",
                ["--project-id", args.project_id, "--days", str(args.days)]
            )
            if ret != 0:
                logger.warning("Insights generation failed (non-fatal)")
    else:
        logger.info("⏭️  Skipping insights generation")
    
    logger.info("=" * 60)
    logger.info("✅ Pipeline completed successfully")
    logger.info("=" * 60)
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
