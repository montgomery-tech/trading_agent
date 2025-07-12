#!/bin/bash

# Quick fix to disable rate limiting for admin testing
echo "🔧 Disabling Rate Limiting for Admin Testing"
echo "============================================="

# Check current .env file
echo "📋 Current rate limiting settings in .env:"
grep -E "RATE_LIMIT" .env | head -10

echo ""
echo "🔧 Creating backup and updating .env..."

# Create backup
cp .env .env.backup.$(date +%Y%m%d_%H%M%S)

# Temporarily disable rate limiting by updating .env
sed -i.tmp 's/RATE_LIMIT_ENABLED=true/RATE_LIMIT_ENABLED=false/' .env

echo "✅ Updated RATE_LIMIT_ENABLED to false"

# Alternative: Increase rate limits dramatically
echo ""
echo "🔧 Alternative: Increasing rate limits instead of disabling..."

# Add or update rate limit values to be very permissive
if grep -q "RATE_LIMIT_ADMIN_REQUESTS" .env; then
    sed -i.tmp 's/RATE_LIMIT_ADMIN_REQUESTS=.*/RATE_LIMIT_ADMIN_REQUESTS=1000/' .env
else
    echo "RATE_LIMIT_ADMIN_REQUESTS=1000" >> .env
fi

if grep -q "RATE_LIMIT_REQUESTS_PER_MINUTE" .env; then
    sed -i.tmp 's/RATE_LIMIT_REQUESTS_PER_MINUTE=.*/RATE_LIMIT_REQUESTS_PER_MINUTE=1000/' .env
else
    echo "RATE_LIMIT_REQUESTS_PER_MINUTE=1000" >> .env
fi

echo "✅ Increased admin rate limits to 1000 requests"

echo ""
echo "📋 Updated rate limiting settings:"
grep -E "RATE_LIMIT" .env | head -10

echo ""
echo "🔄 Now restart your FastAPI server:"
echo "   python3 main.py"
echo ""
echo "🧪 Then test the admin endpoints:"
echo "   curl -X POST http://localhost:8000/api/v1/admin/users -H 'Content-Type: application/json' -d '{\"email\":\"test@example.com\",\"full_name\":\"Test User\",\"role\":\"trader\"}'"
echo ""
echo "⚠️  Remember to re-enable rate limiting for production!"

# Clean up temp files
rm -f .env.tmp
