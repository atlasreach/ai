#!/bin/bash
# Start the Content Studio API

cd "$(dirname "$0")/.."
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

echo "🚀 Starting Content Studio API..."
uvicorn api.studio_api:app --host 0.0.0.0 --port 8002 --reload
