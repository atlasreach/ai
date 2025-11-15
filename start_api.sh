#!/bin/bash
# Kill any existing API servers
pkill -9 -f "uvicorn.*8002" 2>/dev/null

cd /workspaces/ai

echo "🚀 Starting API server..."
python -m uvicorn api.studio_api:app --reload --port 8002 --host 0.0.0.0 &

# Wait for it to start
sleep 5

# Check if it's running
if curl -s http://localhost:8002/docs > /dev/null; then
    echo "✅ API is running on http://localhost:8002"
    echo "📖 Docs: http://localhost:8002/docs"
else
    echo "❌ API failed to start. Check logs:"
    tail -20 /tmp/api.log 2>/dev/null || echo "No logs found"
fi
