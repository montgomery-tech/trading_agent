#!/bin/bash

echo "🔒 COMPREHENSIVE SECURITY VALIDATION"
echo "==================================="

# Use tokens from our previous test
TRADER_TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI4ZDNkNjNiYy1iNjk1LTRmYjItODI2Ny01ZTkwMjc0MjlhYmYiLCJ1c2VybmFtZSI6InRyYWRlci50ZXN0LjE3NTI2MzQ4NTkiLCJlbWFpbCI6InRyYWRlci50ZXN0LjE3NTI2MzQ4NTlAZXhhbXBsZS5jb20iLCJyb2xlIjoidHJhZGVyIiwidG9rZW5fdHlwZSI6ImFjY2VzcyIsImlhdCI6MTc1MjYzNDg2MSwiZXhwIjoxNzUyNjM2NjYxLCJqdGkiOiIwNzgzOTc0MC1iYWUxLTRjNDgtYjQwYS05ZDQwMmYzOTc4OWIiLCJpc3MiOiJiYWxhbmNlLXRyYWNraW5nLWFwaSIsImF1ZCI6ImJhbGFuY2UtdHJhY2tpbmctdXNlcnMifQ.1FasCSkHaGreFMi9Bn0IyhqHeh5ngICsS9tumUMz7Ag"

VIEWER_TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJlNjY2ZTJhNS02MWM4LTQzZDEtODVkOS0xYzY4NWJiMmJjMGQiLCJ1c2VybmFtZSI6InZpZXdlci50ZXN0LjE3NTI2MzQ4NTkiLCJlbWFpbCI6InZpZXdlci50ZXN0LjE3NTI2MzQ4NTlAZXhhbXBsZS5jb20iLCJyb2xlIjoidmlld2VyIiwidG9rZW5fdHlwZSI6ImFjY2VzcyIsImlhdCI6MTc1MjYzNDg2MSwiZXhwIjoxNzUyNjM2NjYxLCJqdGkiOiI2NTFiZDM4NS0zOTQ5LTQ1ZWQtYTU5Ni1mMzZiMjU0NDM5N2YiLCJpc3MiOiJiYWxhbmNlLXRyYWNraW5nLWFwaSIsImF1ZCI6ImJhbGFuY2UtdHJhY2tpbmctdXNlcnMifQ.wpuErHPW3gkZLF7sQBAORRn4c0n2Heo_Cp5vn9i7ONc"

echo ""
echo "🚨 CRITICAL: Testing Cross-User Data Access"
echo "============================================"

# Test 1: Trader trying to access admin user data
echo "Test 1: Trader accessing admin profile (garrett_admin)..."
RESPONSE1=$(curl -s -w "%{http_code}" -H "Authorization: Bearer $TRADER_TOKEN" \
           "http://localhost:8000/api/v1/users/garrett_admin" | tail -c 3)
if [ "$RESPONSE1" = "403" ] || [ "$RESPONSE1" = "401" ]; then
    echo "   ✅ SECURE: Trader blocked from admin data ($RESPONSE1)"
else
    echo "   🚨 SECURITY RISK: Trader can access admin data ($RESPONSE1)"
fi

# Test 2: Viewer trying to access trader data  
echo "Test 2: Viewer accessing trader profile..."
RESPONSE2=$(curl -s -w "%{http_code}" -H "Authorization: Bearer $VIEWER_TOKEN" \
           "http://localhost:8000/api/v1/users/trader.test.1752634859" | tail -c 3)
if [ "$RESPONSE2" = "403" ] || [ "$RESPONSE2" = "401" ]; then
    echo "   ✅ SECURE: Viewer blocked from trader data ($RESPONSE2)"
else
    echo "   🚨 SECURITY RISK: Viewer can access trader data ($RESPONSE2)"
fi

# Test 3: User accessing their own data (should work)
echo "Test 3: Trader accessing own profile..."
RESPONSE3=$(curl -s -w "%{http_code}" -H "Authorization: Bearer $TRADER_TOKEN" \
           "http://localhost:8000/api/v1/users/trader.test.1752634859" | tail -c 3)
if [ "$RESPONSE3" = "200" ]; then
    echo "   ✅ CORRECT: User can access own data ($RESPONSE3)"
else
    echo "   ❌ PROBLEM: User cannot access own data ($RESPONSE3)"
fi

echo ""
echo "📚 Testing API Documentation"
echo "============================"

# Test if docs are accessible
echo "Checking API documentation availability..."
DOC_STATUS=$(curl -s -w "%{http_code}" "http://localhost:8000/docs" | tail -c 3)
if [ "$DOC_STATUS" = "200" ]; then
    echo "   ✅ API docs accessible at /docs"
else
    echo "   ❌ API docs not accessible ($DOC_STATUS)"
fi

# Test OpenAPI spec
echo "Checking OpenAPI specification..."
API_STATUS=$(curl -s -w "%{http_code}" "http://localhost:8000/openapi.json" | tail -c 3)
if [ "$API_STATUS" = "200" ]; then
    echo "   ✅ OpenAPI spec accessible at /openapi.json"
    
    # Check if forced password change is documented
    curl -s "http://localhost:8000/openapi.json" | grep -q "forced-password-change" && \
        echo "   ✅ Forced password change endpoint documented" || \
        echo "   ⚠️  Forced password change endpoint may not be documented"
else
    echo "   ❌ OpenAPI spec not accessible ($API_STATUS)"
fi

echo ""
echo "🎯 SECURITY ASSESSMENT SUMMARY"
echo "==============================="
echo "Visit http://localhost:8000/docs to manually verify:"
echo "1. /api/v1/auth/login shows 403 response for password_change_required"
echo "2. /api/v1/auth/forced-password-change endpoint is documented"
echo "3. User profile endpoints show proper access restrictions"

