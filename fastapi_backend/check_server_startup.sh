#!/bin/bash

echo "🔍 Checking Server Startup Code"
echo "==============================="

echo "📋 Looking for server startup code in main.py..."

# Check if main.py has uvicorn.run or if __name__ == "__main__"
if grep -q "uvicorn.run\|__main__" main.py; then
    echo "✅ Server startup code found"
    echo ""
    echo "📋 Server startup section:"
    grep -n -A 10 -B 2 "uvicorn.run\|__main__" main.py
else
    echo "❌ No server startup code found in main.py"
    echo ""
    echo "🔍 End of main.py file:"
    tail -10 main.py
    echo ""
    echo "❌ main.py is missing the server startup code!"
fi

echo ""
echo "📋 Checking if uvicorn is installed..."
pip3 list | grep uvicorn || echo "❌ uvicorn not found"

echo ""
echo "🔧 If startup code is missing, it should look like this:"
echo "------------------------------------------------------"
cat << 'EOF'

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# Server startup
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0", 
        port=8000,
        reload=True,
        log_level="info"
    )
EOF
