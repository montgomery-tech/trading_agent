#!/bin/bash
# Server Restart Verification and Force Reload

echo "🔄 SERVER RESTART VERIFICATION AND FORCE RELOAD"
echo "================================================"

echo "📋 Step 1: Check current server process..."
PIDS=$(pgrep -f "uvicorn main:app")
if [[ -n "$PIDS" ]]; then
    echo "🟡 Server is currently running with PIDs: $PIDS"
    echo "   This explains why changes aren't taking effect!"
    echo ""
    echo "🛑 Stopping all uvicorn processes..."
    kill $PIDS
    sleep 3
    
    # Double-check they're stopped
    REMAINING=$(pgrep -f "uvicorn main:app")
    if [[ -n "$REMAINING" ]]; then
        echo "⚠️  Some processes still running, force killing..."
        kill -9 $REMAINING
        sleep 2
    fi
    echo "✅ All server processes stopped"
else
    echo "✅ No server processes running"
fi

echo ""
echo "🧹 Step 2: Clear Python cache..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find . -name "*.pyc" -delete 2>/dev/null
echo "✅ Python cache cleared"

echo ""
echo "🚀 Step 3: Starting server with debug logging..."
echo "================================================"
echo ""
echo "🔥 CRITICAL: The server MUST be restarted for changes to take effect!"
echo "Running: python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --log-level debug --reload"
echo ""
echo "👀 Watch for these startup messages:"
echo "   - 'Configuration loaded'"
echo "   - 'Database initialized'"
echo "   - No import errors"
echo ""
echo "🧪 After server starts, run this test:"
echo "   ./test_admin_auth.sh"
echo ""
echo "Press Ctrl+C to cancel, or Enter to start server now..."

read -t 5

echo ""
echo "🎯 Starting server..."
echo "===================="

# Start server with debug logging and auto-reload
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --log-level debug --reload
