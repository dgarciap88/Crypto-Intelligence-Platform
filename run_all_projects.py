#!/usr/bin/env python3
"""
Run pipeline for all projects defined in projects.yaml.

This script orchestrates the full data pipeline for multiple projects:
1. For each project in projects.yaml:
   - Ingest GitHub data
   - Normalize events
   - Generate AI insights

Usage:
  python run_all_projects.py [--days 7] [--skip-ingest] [--projects-file projects.yaml]
  
Options:
  --days N: Number of days of history to process (default: 7)
  --skip-ingest: Skip GitHub ingestion, only normalize + insights
  --skip-insights: Skip AI insights generation
  --projects-file: Path to projects.yaml (default: projects.yaml)
  --only: Process only specific project IDs (e.g., --only ethereum solana)
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from pathlib import Path
from typing import Dict, Any

import yaml

# Add ingestion directory to path
sys.path.insert(0, str(Path(__file__).parent / "ingestion"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def load_projects_config(file_path: str) -> list[Dict[str, Any]]:
    """Load projects configuration from YAML file."""
    with open(file_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    
    if not config or "projects" not in config:
        raise ValueError("Invalid projects.yaml format - missing 'projects' key")
    
    return config["projects"]


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
    logger.info("")
    logger.info("  Stage: %s", stage_name)
    logger.info("  " + "-" * 50)
    
    try:
        # Dynamic import
        if "." in module_name:
            parts = module_name.split(".")
            module = __import__(f"ingestion.{module_name}", fromlist=[parts[-1]])
        else:
            module = __import__(module_name)
        
        # Run main function
        result = module.main(args)
        
        if result != 0:
            logger.error("  ❌ Stage '%s' failed with exit code %d", stage_name, result)
            return result
        
        logger.info("  ✅ Stage '%s' completed successfully", stage_name)
        return 0
        
    except Exception as e:
        logger.error("  ❌ Stage '%s' failed with exception: %s", stage_name, e)
        return 1


def create_project_yaml(project_config: Dict[str, Any], temp_dir: Path) -> Path:
    """Create a temporary project.yaml for a single project."""
    project_id = project_config["project_id"]
    yaml_path = temp_dir / f"{project_id}.yaml"
    
    with open(yaml_path, "w", encoding="utf-8") as f:
        yaml.dump(project_config, f)
    
    return yaml_path


def run_pipeline_for_project(
    project_config: Dict[str, Any],
    days: int,
    skip_ingest: bool,
    skip_insights: bool,
    temp_dir: Path
) -> int:
    """Run the complete pipeline for a single project."""
    project_id = project_config["project_id"]
    project_name = project_config["name"]
    
    logger.info("")
    logger.info("=" * 70)
    logger.info("🚀 Processing: %s (%s)", project_name, project_id)
    logger.info("=" * 70)
    
    start_time = time.time()
    
    # Create temporary project YAML
    project_yaml = create_project_yaml(project_config, temp_dir)
    
    try:
        # Stage 1: Ingest GitHub data
        if not skip_ingest:
            result = run_stage(
                "GitHub Ingestion",
                "github.ingest_github",
                ["--project", str(project_yaml)]
            )
            if result != 0:
                logger.error("❌ Failed to ingest GitHub data for %s", project_id)
                return result
        else:
            logger.info("  ⏭️  Skipping GitHub ingestion")
        
        # Stage 2: Normalize events
        result = run_stage(
            "Event Normalization",
            "normalize",
            ["--project-id", project_id, "--batch-size", "100"]
        )
        if result != 0:
            logger.error("❌ Failed to normalize events for %s", project_id)
            return result
        
        # Stage 3: Generate AI insights
        if not skip_insights:
            result = run_stage(
                "AI Insights Generation",
                "generate_insights",
                ["--project-id", project_id, "--days", str(days)]
            )
            if result != 0:
                logger.warning("⚠️  Failed to generate insights for %s (continuing)", project_id)
                # Don't fail the whole pipeline on insights errors
        else:
            logger.info("  ⏭️  Skipping AI insights")
        
        elapsed = time.time() - start_time
        logger.info("")
        logger.info("✅ Completed %s in %.1f seconds", project_id, elapsed)
        return 0
        
    except Exception as e:
        logger.error("❌ Error processing %s: %s", project_id, e)
        return 1
    
    finally:
        # Cleanup temporary YAML
        if project_yaml.exists():
            project_yaml.unlink()


def main(argv: list[str] | None = None) -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Run pipeline for all projects")
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="Number of days of history to process (default: 7)"
    )
    parser.add_argument(
        "--skip-ingest",
        action="store_true",
        help="Skip GitHub ingestion stage"
    )
    parser.add_argument(
        "--skip-insights",
        action="store_true",
        help="Skip AI insights generation stage"
    )
    parser.add_argument(
        "--projects-file",
        default="projects.yaml",
        help="Path to projects.yaml (default: projects.yaml)"
    )
    parser.add_argument(
        "--only",
        nargs="+",
        help="Process only these project IDs (e.g., --only ethereum solana)"
    )
    args = parser.parse_args(argv)

    logger.info("=" * 70)
    logger.info("Crypto Intelligence Platform - Batch Pipeline")
    logger.info("=" * 70)
    logger.info("Days: %d", args.days)
    logger.info("Projects file: %s", args.projects_file)
    if args.only:
        logger.info("Filtering: %s", ", ".join(args.only))
    
    # Check environment
    if not check_env_vars():
        return 2
    
    # Load projects
    projects_file = Path(args.projects_file)
    if not projects_file.exists():
        logger.error("Projects file not found: %s", projects_file)
        return 1
    
    try:
        all_projects = load_projects_config(str(projects_file))
        logger.info("Loaded %d projects", len(all_projects))
    except Exception as e:
        logger.error("Error loading projects.yaml: %s", e)
        return 1
    
    # Filter projects if --only specified
    if args.only:
        projects_to_process = [
            p for p in all_projects
            if p["project_id"] in args.only
        ]
        
        if not projects_to_process:
            logger.error("No matching projects found for: %s", args.only)
            return 1
        
        logger.info("Processing %d projects (filtered)", len(projects_to_process))
    else:
        projects_to_process = all_projects
    
    # Create temp directory for project YAMLs
    temp_dir = Path(__file__).parent / ".temp_projects"
    temp_dir.mkdir(exist_ok=True)
    
    # Process each project
    total_start = time.time()
    failed_projects = []
    
    try:
        for i, project_config in enumerate(projects_to_process, 1):
            project_id = project_config["project_id"]
            
            logger.info("")
            logger.info("📊 Progress: %d/%d", i, len(projects_to_process))
            
            result = run_pipeline_for_project(
                project_config,
                args.days,
                args.skip_ingest,
                args.skip_insights,
                temp_dir
            )
            
            if result != 0:
                failed_projects.append(project_id)
            
            # Small delay between projects to avoid rate limits
            if i < len(projects_to_process):
                logger.info("Waiting 2 seconds before next project...")
                time.sleep(2)
        
        # Summary
        total_elapsed = time.time() - total_start
        logger.info("")
        logger.info("=" * 70)
        logger.info("🏁 Pipeline Complete")
        logger.info("=" * 70)
        logger.info("Total time: %.1f seconds", total_elapsed)
        logger.info("Projects processed: %d", len(projects_to_process))
        logger.info("Successful: %d", len(projects_to_process) - len(failed_projects))
        
        if failed_projects:
            logger.warning("Failed: %d (%s)", len(failed_projects), ", ".join(failed_projects))
            return 1
        else:
            logger.info("✅ All projects completed successfully!")
            return 0
    
    finally:
        # Cleanup temp directory
        try:
            for yaml_file in temp_dir.glob("*.yaml"):
                yaml_file.unlink()
            temp_dir.rmdir()
        except Exception as e:
            logger.warning("Failed to cleanup temp directory: %s", e)


if __name__ == "__main__":
    raise SystemExit(main())
