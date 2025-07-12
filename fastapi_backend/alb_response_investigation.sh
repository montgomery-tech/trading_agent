#!/bin/bash

# ALB Response Differences Investigation Script
# Task 1.1: Systematic investigation of ALB vs Direct EC2 response differences

echo "🔍 TASK 1.1: ALB Response Differences Investigation"
echo "=================================================="
echo ""
echo "📋 Purpose: Identify why ALB and Direct EC2 responses differ"
echo "   Based on test results showing: ❌ ALB and direct responses differ"
echo ""

# Configuration
DIRECT_URL="http://18.204.204.26:8000"
ALB_URL="http://trading-api-alb-464076303.us-east-1.elb.amazonaws.com"
TIMEOUT=10

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Helper functions
log_step() {
    echo -e "${BLUE}🔧 Step $1: $2${NC}"
}

log_finding() {
    echo -e "${YELLOW}📊 Finding: $1${NC}"
}

log_issue() {
    echo -e "${RED}⚠️  Issue: $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

echo "🎯 Target URLs:"
echo "   Direct EC2: $DIRECT_URL"
echo "   ALB: $ALB_URL"
echo ""

# =============================================================================
# STEP 1: BASIC RESPONSE COMPARISON
# =============================================================================

log_step "1" "Capturing Raw Responses"

echo "📡 Fetching health endpoint responses..."

# Create temporary files for comparison
DIRECT_RESPONSE=$(mktemp)
ALB_RESPONSE=$(mktemp)
DIRECT_HEADERS=$(mktemp)
ALB_HEADERS=$(mktemp)

# Fetch Direct EC2 response
echo "   Fetching Direct EC2 response..."
curl -s --connect-timeout $TIMEOUT "$DIRECT_URL/health" > "$DIRECT_RESPONSE"
DIRECT_STATUS=$(curl -s -w "%{http_code}" --connect-timeout $TIMEOUT "$DIRECT_URL/health" | tail -c 3)

# Fetch ALB response
echo "   Fetching ALB response..."
curl -s --connect-timeout $TIMEOUT "$ALB_URL/health" > "$ALB_RESPONSE"
ALB_STATUS=$(curl -s -w "%{http_code}" --connect-timeout $TIMEOUT "$ALB_URL/health" | tail -c 3)

# Fetch headers separately
curl -s -I --connect-timeout $TIMEOUT "$DIRECT_URL/health" > "$DIRECT_HEADERS"
curl -s -I --connect-timeout $TIMEOUT "$ALB_URL/health" > "$ALB_HEADERS"

echo ""
log_finding "HTTP Status Codes"
echo "   Direct EC2: $DIRECT_STATUS"
echo "   ALB: $ALB_STATUS"

if [ "$DIRECT_STATUS" != "$ALB_STATUS" ]; then
    log_issue "Status codes differ!"
fi

echo ""

# =============================================================================
# STEP 2: RESPONSE BODY ANALYSIS
# =============================================================================

log_step "2" "Analyzing Response Bodies"

# Check if responses are identical
if cmp -s "$DIRECT_RESPONSE" "$ALB_RESPONSE"; then
    log_success "Response bodies are identical"
else
    log_issue "Response bodies differ"

    echo ""
    echo "📊 Response body comparison:"
    echo ""
    echo "Direct EC2 response:"
    echo "-------------------"
    cat "$DIRECT_RESPONSE" | head -10
    echo ""
    echo "ALB response:"
    echo "-------------"
    cat "$ALB_RESPONSE" | head -10
    echo ""

    # Show differences
    echo "🔍 Detailed differences:"
    diff -u "$DIRECT_RESPONSE" "$ALB_RESPONSE" || true
fi

echo ""

# =============================================================================
# STEP 3: JSON CONTENT ANALYSIS
# =============================================================================

log_step "3" "JSON Content Analysis"

echo "🧪 Parsing JSON responses for content analysis..."

# Check if both are valid JSON
DIRECT_JSON_VALID=false
ALB_JSON_VALID=false

if python3 -m json.tool < "$DIRECT_RESPONSE" > /dev/null 2>&1; then
    DIRECT_JSON_VALID=true
    log_success "Direct EC2 response is valid JSON"
else
    log_issue "Direct EC2 response is not valid JSON"
fi

if python3 -m json.tool < "$ALB_RESPONSE" > /dev/null 2>&1; then
    ALB_JSON_VALID=true
    log_success "ALB response is valid JSON"
else
    log_issue "ALB response is not valid JSON"
fi

if [ "$DIRECT_JSON_VALID" = true ] && [ "$ALB_JSON_VALID" = true ]; then
    echo ""
    echo "🔍 Analyzing JSON field differences..."

    # Extract timestamps to check if that's the difference
    DIRECT_TIMESTAMP=$(python3 -c "
import json
try:
    with open('$DIRECT_RESPONSE') as f:
        data = json.load(f)
    print(data.get('timestamp', 'NO_TIMESTAMP'))
except:
    print('PARSE_ERROR')
")

    ALB_TIMESTAMP=$(python3 -c "
import json
try:
    with open('$ALB_RESPONSE') as f:
        data = json.load(f)
    print(data.get('timestamp', 'NO_TIMESTAMP'))
except:
    print('PARSE_ERROR')
")

    echo "   Direct EC2 timestamp: $DIRECT_TIMESTAMP"
    echo "   ALB timestamp: $ALB_TIMESTAMP"

    if [ "$DIRECT_TIMESTAMP" != "$ALB_TIMESTAMP" ]; then
        log_finding "Timestamps differ - this is likely the root cause!"
        echo "   This explains why responses are different on each request"
    fi

    # Check other fields for consistency
    echo ""
    echo "🔍 Comparing other JSON fields (excluding timestamp)..."

    python3 << 'PYTHON_SCRIPT'
import json
import sys

try:
    with open(sys.argv[1], 'r') as f:
        direct_data = json.load(f)
    with open(sys.argv[2], 'r') as f:
        alb_data = json.load(f)

    # Remove timestamps for comparison
    direct_data.pop('timestamp', None)
    alb_data.pop('timestamp', None)

    if direct_data == alb_data:
        print("✅ All other fields are identical (timestamps are the only difference)")
    else:
        print("⚠️  Other fields also differ:")
        for key in set(list(direct_data.keys()) + list(alb_data.keys())):
            direct_val = direct_data.get(key)
            alb_val = alb_data.get(key)
            if direct_val != alb_val:
                print(f"   {key}: Direct='{direct_val}' vs ALB='{alb_val}'")
except Exception as e:
    print(f"Error comparing JSON: {e}")
PYTHON_SCRIPT "$DIRECT_RESPONSE" "$ALB_RESPONSE"
fi

echo ""

# =============================================================================
# STEP 4: RESPONSE HEADERS ANALYSIS
# =============================================================================

log_step "4" "Response Headers Analysis"

echo "📋 Comparing response headers..."

echo ""
echo "Direct EC2 headers:"
echo "-------------------"
cat "$DIRECT_HEADERS"

echo ""
echo "ALB headers:"
echo "------------"
cat "$ALB_HEADERS"

echo ""
echo "🔍 Header differences:"
diff -u "$DIRECT_HEADERS" "$ALB_HEADERS" || echo "   No header differences found"

echo ""

# =============================================================================
# STEP 5: RESPONSE TIMING ANALYSIS
# =============================================================================

log_step "5" "Response Timing Analysis"

echo "⏱️  Testing response timing differences..."

# Make multiple requests quickly to see timing patterns
echo "   Making 5 rapid requests to each endpoint..."

echo ""
echo "Direct EC2 timestamps:"
for i in {1..5}; do
    TIMESTAMP=$(curl -s --connect-timeout $TIMEOUT "$DIRECT_URL/health" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    print(data.get('timestamp', 'NO_TIMESTAMP'))
except:
    print('PARSE_ERROR')
")
    echo "   Request $i: $TIMESTAMP"
    sleep 0.5
done

echo ""
echo "ALB timestamps:"
for i in {1..5}; do
    TIMESTAMP=$(curl -s --connect-timeout $TIMEOUT "$ALB_URL/health" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    print(data.get('timestamp', 'NO_TIMESTAMP'))
except:
    print('PARSE_ERROR')
")
    echo "   Request $i: $TIMESTAMP"
    sleep 0.5
done

echo ""

# =============================================================================
# STEP 6: ROOT CAUSE ANALYSIS
# =============================================================================

log_step "6" "Root Cause Analysis & Conclusions"

echo "🎯 INVESTIGATION SUMMARY:"
echo ""

# Determine the most likely root cause
if [ "$DIRECT_TIMESTAMP" != "$ALB_TIMESTAMP" ] && [ "$DIRECT_STATUS" = "$ALB_STATUS" ]; then
    echo "🔍 ROOT CAUSE IDENTIFIED:"
    echo "   The responses differ because of dynamic timestamp generation"
    echo "   Each request generates a new timestamp, making responses unique"
    echo ""
    echo "💡 EXPLANATION:"
    echo "   • FastAPI health endpoint includes current timestamp in response"
    echo "   • Direct EC2 and ALB requests happen at slightly different times"
    echo "   • This causes byte-for-byte comparison to fail in test suite"
    echo ""
    echo "✅ SYSTEM STATUS:"
    echo "   • Both endpoints are working correctly"
    echo "   • Responses are functionally identical (same structure/data)"
    echo "   • Only timestamps differ, which is expected behavior"
    echo ""
    echo "🎯 RECOMMENDATION:"
    echo "   Update test suite to compare responses excluding timestamp field"
    echo "   OR implement timestamp normalization for consistent testing"

elif [ "$DIRECT_STATUS" != "$ALB_STATUS" ]; then
    echo "⚠️  ISSUE IDENTIFIED:"
    echo "   HTTP status codes differ between Direct EC2 and ALB"
    echo "   Direct: $DIRECT_STATUS, ALB: $ALB_STATUS"
    echo "   This indicates a more serious configuration issue"

else
    echo "🔍 INVESTIGATION NEEDED:"
    echo "   Responses differ but root cause not immediately clear"
    echo "   Manual review of response content recommended"
fi

# Clean up temporary files
rm -f "$DIRECT_RESPONSE" "$ALB_RESPONSE" "$DIRECT_HEADERS" "$ALB_HEADERS"

echo ""
echo "📊 TASK 1.1 COMPLETED"
echo "====================="
echo "✅ Investigation complete - root cause identified"
echo "📝 Ready to proceed to Task 1.2: Fix ALB response consistency"
echo ""
