#!/bin/bash
# Container initialization script
# Runs when Docker container starts

set -e

echo "=========================================="
echo "Crypto Intelligence Platform - Starting"
echo "=========================================="

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL..."
until python -c "import psycopg2; import os; psycopg2.connect(os.getenv('DATABASE_URL')).close()" 2>/dev/null; do
    echo "  PostgreSQL not ready yet, waiting..."
    sleep 2
done
echo "✅ PostgreSQL is ready"

# Setup all projects (idempotent - safe to run multiple times)
echo ""
echo "Setting up projects..."
python setup_all_projects.py

# Run the main pipeline
echo ""
echo "Starting pipeline in continuous mode..."
exec python -u run_all_projects.py --continuous "$@"
