#!/bin/bash

echo "🔒 COMPREHENSIVE SECURITY VALIDATION - FIXED VERSION"
echo "===================================================="

# Configuration
API_BASE="http://localhost:8000"

# Use existing tokens from previous test (adjust if needed)
ADMIN_TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJmYjkyZGM2NS0yYzU1LTQ3ZTYtOGZjOS1lYzFjZTViMTA5ZjAiLCJ1c2VybmFtZSI6ImdhcnJldHRfYWRtaW4iLCJlbWFpbCI6ImFkbWluQGV4YW1wbGUuY29tIiwicm9sZSI6ImFkbWluIiwidG9rZW5fdHlwZSI6ImFjY2VzcyIsImlhdCI6MTcyMTI0OTY2NywiZXhwIjoxNzIxMjUxNDY3LCJqdGkiOiI5YWE4YTNhZC05YmI4LTQ3YjItOTFkMy0zMjBjOGI3YTdkZTEiLCJpc3MiOiJiYWxhbmNlLXRyYWNraW5nLWFwaSIsImF1ZCI6ImJhbGFuY2UtdHJhY2tpbmctdXNlcnMifQ.abc123"

TRADER_TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI4ZDNkNjNiYy1iNjk1LTRmYjItODI2Ny01ZTkwMjc0MjlhYmYiLCJ1c2VybmFtZSI6InRyYWRlci50ZXN0LjE3NTI2MzQ4NTkiLCJlbWFpbCI6InRyYWRlci50ZXN0LjE3NTI2MzQ4NTlAZXhhbXBsZS5jb20iLCJyb2xlIjoidHJhZGVyIiwidG9rZW5fdHlwZSI6ImFjY2VzcyIsImlhdCI6MTc1MjYzNDg2MSwiZXhwIjoxNzUyNjM2NjYxLCJqdGkiOiIwNzgzOTc0MC1iYWUxLTRjNDgtYjQwYS05ZDQwMmYzOTc4OWIiLCJpc3MiOiJiYWxhbmNlLXRyYWNraW5nLWFwaSIsImF1ZCI6ImJhbGFuY2UtdHJhY2tpbmctdXNlcnMifQ.1FasCSkHaGreFMi9Bn0IyhqHeh5ngICsS9tumUMz7Ag"

VIEWER_TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJlNjY2ZTJhNS02MWM4LTQzZDEtODVkOS0xYzY4NWJiMmJjMGQiLCJ1c2VybmFtZSI6InZpZXdlci50ZXN0LjE3NTI2MzQ4NTkiLCJlbWFpbCI6InZpZXdlci50ZXN0LjE3NTI2MzQ4NTlAZXhhbXBsZS5jb20iLCJyb2xlIjoidmlld2VyIiwidG9rZW5fdHlwZSI6ImFjY2VzcyIsImlhdCI6MTc1MjYzNDg2MSwiZXhwIjoxNzUyNjM2NjYxLCJqdGkiOiI2NTFiZDM4NS0zOTQ5LTQ1ZWQtYTU5Ni1mMzZiMjU0NDM5N2YiLCJpc3MiOiJiYWxhbmNlLXRyYWNraW5nLWFwaSIsImF1ZCI6ImJhbGFuY2UtdHJhY2tpbmctdXNlcnMifQ.wpuErHPW3gkZLF7sQBAORRn4c0n2Heo_Cp5vn9i7ONc"

echo ""
echo "🚨 CRITICAL: Testing Cross-User Data Access (EXPECTED: ALL BLOCKED)"
echo "=================================================================="

# Test 1: Trader trying to access admin user data (SHOULD BE BLOCKED)
echo "Test 1: Trader accessing admin profile (garrett_admin)..."
RESPONSE1=$(curl -s -w "%{http_code}" -H "Authorization: Bearer $TRADER_TOKEN" \
           "$API_BASE/api/v1/users/garrett_admin" | tail -c 3)
if [ "$RESPONSE1" = "403" ] || [ "$RESPONSE1" = "401" ]; then
    echo "   ✅ SECURE: Trader blocked from admin data ($RESPONSE1)"
else
    echo "   🚨 SECURITY RISK: Trader can access admin data ($RESPONSE1)"
fi

# Test 2: Viewer trying to access trader data (SHOULD BE BLOCKED)
echo "Test 2: Viewer accessing trader profile..."
RESPONSE2=$(curl -s -w "%{http_code}" -H "Authorization: Bearer $VIEWER_TOKEN" \
           "$API_BASE/api/v1/users/trader.test.1752634859" | tail -c 3)
if [ "$RESPONSE2" = "403" ] || [ "$RESPONSE2" = "401" ]; then
    echo "   ✅ SECURE: Viewer blocked from trader data ($RESPONSE2)"
else
    echo "   🚨 SECURITY RISK: Viewer can access trader data ($RESPONSE2)"
fi

# Test 3: User accessing their own data (SHOULD WORK)
echo "Test 3: Trader accessing own profile..."
RESPONSE3=$(curl -s -w "%{http_code}" -H "Authorization: Bearer $TRADER_TOKEN" \
           "$API_BASE/api/v1/users/trader.test.1752634859" | tail -c 3)
if [ "$RESPONSE3" = "200" ]; then
    echo "   ✅ CORRECT: User can access own data ($RESPONSE3)"
else
    echo "   ❌ PROBLEM: User cannot access own data ($RESPONSE3)"
fi

# Test 4: Admin accessing any user data (SHOULD WORK IF ADMIN ROLE IMPLEMENTED)
echo "Test 4: Admin accessing trader profile..."
RESPONSE4=$(curl -s -w "%{http_code}" -H "Authorization: Bearer $ADMIN_TOKEN" \
           "$API_BASE/api/v1/users/trader.test.1752634859" | tail -c 3)
if [ "$RESPONSE4" = "200" ]; then
    echo "   ✅ CORRECT: Admin can access user data ($RESPONSE4)"
elif [ "$RESPONSE4" = "403" ] || [ "$RESPONSE4" = "401" ]; then
    echo "   ⚠️  INFO: Admin blocked (check admin role config) ($RESPONSE4)"
else
    echo "   ❌ ERROR: Unexpected admin response ($RESPONSE4)"
fi

# Test 5: No authorization header (SHOULD BE BLOCKED)
echo "Test 5: No authorization header..."
RESPONSE5=$(curl -s -w "%{http_code}" "$API_BASE/api/v1/users/garrett_admin" | tail -c 3)
if [ "$RESPONSE5" = "403" ] || [ "$RESPONSE5" = "401" ]; then
    echo "   ✅ SECURE: No auth blocked ($RESPONSE5)"
else
    echo "   🚨 SECURITY RISK: No auth allowed ($RESPONSE5)"
fi

# Test 6: Invalid token (SHOULD BE BLOCKED)
echo "Test 6: Invalid token..."
RESPONSE6=$(curl -s -w "%{http_code}" -H "Authorization: Bearer invalid_token_123" \
           "$API_BASE/api/v1/users/garrett_admin" | tail -c 3)
if [ "$RESPONSE6" = "403" ] || [ "$RESPONSE6" = "401" ]; then
    echo "   ✅ SECURE: Invalid token blocked ($RESPONSE6)"
else
    echo "   🚨 SECURITY RISK: Invalid token allowed ($RESPONSE6)"
fi

echo ""
echo "🎯 SECURITY ASSESSMENT SUMMARY"
echo "==============================="
echo "Expected Results After Fix:"
echo "  Test 1: 403 (Trader blocked from admin data)"
echo "  Test 2: 403 (Viewer blocked from trader data)"  
echo "  Test 3: 200 (User can access own data)"
echo "  Test 4: 200 (Admin can access any data)"
echo "  Test 5: 401/403 (No auth blocked)"
echo "  Test 6: 401/403 (Invalid token blocked)"

echo ""
if [ "$RESPONSE1" = "403" ] && [ "$RESPONSE2" = "403" ] && [ "$RESPONSE3" = "200" ] && \
   ([ "$RESPONSE5" = "401" ] || [ "$RESPONSE5" = "403" ]) && \
   ([ "$RESPONSE6" = "401" ] || [ "$RESPONSE6" = "403" ]); then
    echo "🎉 SECURITY FIXED: User data isolation is now working!"
else
    echo "⚠️  SECURITY ISSUE: Some tests failed - review the results above"
fi
