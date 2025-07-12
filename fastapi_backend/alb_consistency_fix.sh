#!/bin/bash

# ALB Response Consistency Fix - Task 1.2
# Fixes the test suite to properly compare ALB and Direct EC2 responses
# Root cause: Dynamic timestamps make byte-for-byte comparison fail

echo "🔧 TASK 1.2: Fix ALB Response Consistency"
echo "========================================="
echo ""
echo "📋 Issue: Test suite fails because responses have different timestamps"
echo "💡 Solution: Update test suite to normalize timestamps before comparison"
echo ""

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

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_info() {
    echo -e "${YELLOW}ℹ️  $1${NC}"
}

# =============================================================================
# STEP 1: BACKUP ORIGINAL TEST SUITE
# =============================================================================

log_step "1" "Backup Original Test Suite"

if [ -f "api_test_suite.sh" ]; then
    cp api_test_suite.sh api_test_suite.sh.backup.$(date +%Y%m%d_%H%M%S)
    log_success "Original test suite backed up"
else
    echo "❌ api_test_suite.sh not found in current directory"
    exit 1
fi

echo ""

# =============================================================================
# STEP 2: CREATE TIMESTAMP NORMALIZATION FUNCTION
# =============================================================================

log_step "2" "Create Timestamp Normalization Function"

# Create the normalization function
cat > normalize_response.py << 'PYTHON_SCRIPT'
#!/usr/bin/env python3
"""
Response normalization utility for ALB consistency testing.
Removes dynamic timestamps to enable accurate response comparison.
"""

import json
import sys
import re

def normalize_health_response(response_text):
    """
    Normalize health response by replacing timestamp with fixed value.
    This allows consistent comparison between ALB and Direct EC2 responses.
    """
    try:
        # First try to parse as JSON
        data = json.loads(response_text)
        
        # Replace timestamp with normalized value
        if 'timestamp' in data:
            data['timestamp'] = 'NORMALIZED_TIMESTAMP'
        
        # Return normalized JSON (sorted keys for consistency)
        return json.dumps(data, sort_keys=True)
        
    except json.JSONDecodeError:
        # If not JSON, try to normalize timestamp patterns in raw text
        # Pattern matches ISO 8601 timestamps like: 2025-07-11T20:30:33.773482
        timestamp_pattern = r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}'
        normalized = re.sub(timestamp_pattern, 'NORMALIZED_TIMESTAMP', response_text)
        return normalized

def main():
    if len(sys.argv) != 2:
        print("Usage: python3 normalize_response.py '<response_text>'")
        sys.exit(1)
    
    response = sys.argv[1]
    normalized = normalize_health_response(response)
    print(normalized)

if __name__ == "__main__":
    main()
PYTHON_SCRIPT

chmod +x normalize_response.py
log_success "Created response normalization utility"

echo ""

# =============================================================================
# STEP 3: UPDATE TEST SUITE FOR NORMALIZED COMPARISON
# =============================================================================

log_step "3" "Update Test Suite ALB Consistency Test"

# Create the updated ALB consistency test section
cat > alb_consistency_test_fix.txt << 'TEST_FIX'

# Test 7.1: ALB response consistency (FIXED VERSION)
log_test "ALB response consistency test"
ALB_RESPONSES_CONSISTENT=true

for i in {1..3}; do
    ALB_RESP=$(curl -s --connect-timeout $TIMEOUT "$ALB_URL/health")
    DIRECT_RESP=$(curl -s --connect-timeout $TIMEOUT "$DIRECT_URL/health")
    
    # Normalize responses to remove timestamp differences
    ALB_NORMALIZED=$(python3 normalize_response.py "$ALB_RESP")
    DIRECT_NORMALIZED=$(python3 normalize_response.py "$DIRECT_RESP")
    
    if [[ "$ALB_NORMALIZED" != "$DIRECT_NORMALIZED" ]]; then
        ALB_RESPONSES_CONSISTENT=false
        echo "   Debug: Response normalization comparison failed"
        echo "   ALB normalized: $ALB_NORMALIZED"
        echo "   Direct normalized: $DIRECT_NORMALIZED"
        break
    fi
    sleep 1
done

if $ALB_RESPONSES_CONSISTENT; then
    log_success "ALB and direct responses are consistent (timestamps normalized)"
else
    log_failure "ALB and direct responses differ (structural differences found)"
fi
TEST_FIX

# Replace the original ALB consistency test in the test suite
sed -i.bak '/# Test 7.1: ALB response consistency/,/log_failure "ALB and direct responses differ"/c\
# Test 7.1: ALB response consistency (FIXED VERSION)\
log_test "ALB response consistency test"\
ALB_RESPONSES_CONSISTENT=true\
\
for i in {1..3}; do\
    ALB_RESP=$(curl -s --connect-timeout $TIMEOUT "$ALB_URL/health")\
    DIRECT_RESP=$(curl -s --connect-timeout $TIMEOUT "$DIRECT_URL/health")\
    \
    # Normalize responses to remove timestamp differences\
    ALB_NORMALIZED=$(python3 normalize_response.py "$ALB_RESP")\
    DIRECT_NORMALIZED=$(python3 normalize_response.py "$DIRECT_RESP")\
    \
    if [[ "$ALB_NORMALIZED" != "$DIRECT_NORMALIZED" ]]; then\
        ALB_RESPONSES_CONSISTENT=false\
        echo "   Debug: Response normalization comparison failed"\
        echo "   ALB normalized: $ALB_NORMALIZED"\
        echo "   Direct normalized: $DIRECT_NORMALIZED"\
        break\
    fi\
    sleep 1\
done\
\
if $ALB_RESPONSES_CONSISTENT; then\
    log_success "ALB and direct responses are consistent (timestamps normalized)"\
else\
    log_failure "ALB and direct responses differ (structural differences found)"\
fi' api_test_suite.sh

log_success "Updated ALB consistency test in test suite"

echo ""

# =============================================================================
# STEP 4: TEST THE FIX
# =============================================================================

log_step "4" "Test the Fix"

echo "🧪 Testing the normalization function..."

# Test the normalization function with sample responses
SAMPLE_DIRECT='{"status":"healthy","timestamp":"2025-07-11T20:30:33.773482","database":{"status":"connected"},"version":"1.0.0"}'
SAMPLE_ALB='{"status":"healthy","timestamp":"2025-07-11T20:30:39.045552","database":{"status":"connected"},"version":"1.0.0"}'

NORMALIZED_DIRECT=$(python3 normalize_response.py "$SAMPLE_DIRECT")
NORMALIZED_ALB=$(python3 normalize_response.py "$SAMPLE_ALB")

echo "   Original responses differ: $([ "$SAMPLE_DIRECT" != "$SAMPLE_ALB" ] && echo "Yes" || echo "No")"
echo "   Normalized responses match: $([ "$NORMALIZED_DIRECT" = "$NORMALIZED_ALB" ] && echo "Yes" || echo "No")"

if [ "$NORMALIZED_DIRECT" = "$NORMALIZED_ALB" ]; then
    log_success "Normalization function working correctly"
else
    echo "❌ Normalization function failed"
    echo "   Direct normalized: $NORMALIZED_DIRECT"
    echo "   ALB normalized: $NORMALIZED_ALB"
    exit 1
fi

echo ""

# =============================================================================
# STEP 5: RUN UPDATED TEST
# =============================================================================

log_step "5" "Run Updated ALB Consistency Test"

echo "🧪 Running the fixed ALB consistency test..."

# Extract and run just the ALB consistency test
DIRECT_URL="http://18.204.204.26:8000"
ALB_URL="http://trading-api-alb-464076303.us-east-1.elb.amazonaws.com"
TIMEOUT=10

# Test function (simplified)
log_test() {
    echo -e "${BLUE}🧪 $1${NC}"
}

log_success_test() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_failure_test() {
    echo -e "${RED}❌ $1${NC}"
}

# Run the actual test
log_test "ALB response consistency test (with timestamp normalization)"
ALB_RESPONSES_CONSISTENT=true

for i in {1..3}; do
    ALB_RESP=$(curl -s --connect-timeout $TIMEOUT "$ALB_URL/health")
    DIRECT_RESP=$(curl -s --connect-timeout $TIMEOUT "$DIRECT_URL/health")
    
    # Normalize responses to remove timestamp differences
    ALB_NORMALIZED=$(python3 normalize_response.py "$ALB_RESP")
    DIRECT_NORMALIZED=$(python3 normalize_response.py "$DIRECT_RESP")
    
    if [[ "$ALB_NORMALIZED" != "$DIRECT_NORMALIZED" ]]; then
        ALB_RESPONSES_CONSISTENT=false
        echo "   Debug: Response normalization comparison failed"
        echo "   ALB normalized: $ALB_NORMALIZED"
        echo "   Direct normalized: $DIRECT_NORMALIZED"
        break
    fi
    sleep 1
done

if $ALB_RESPONSES_CONSISTENT; then
    log_success_test "ALB and direct responses are consistent (timestamps normalized)"
else
    log_failure_test "ALB and direct responses differ (structural differences found)"
fi

echo ""

# =============================================================================
# STEP 6: SUMMARY AND CLEANUP
# =============================================================================

log_step "6" "Summary and Cleanup"

echo "📊 TASK 1.2 RESULTS:"
echo ""

if $ALB_RESPONSES_CONSISTENT; then
    echo "🎉 SUCCESS! ALB response consistency issue RESOLVED"
    echo ""
    echo "✅ What was fixed:"
    echo "   • Test suite now normalizes timestamps before comparison"
    echo "   • ALB and Direct EC2 responses are now recognized as consistent"
    echo "   • False positive test failure eliminated"
    echo ""
    echo "🔧 Changes made:"
    echo "   • Created normalize_response.py utility"
    echo "   • Updated api_test_suite.sh ALB consistency test"
    echo "   • Original test suite backed up"
    echo ""
    echo "📝 Files created/modified:"
    echo "   • normalize_response.py (new utility)"
    echo "   • api_test_suite.sh (updated)"
    echo "   • api_test_suite.sh.backup.* (backup)"
    echo ""
    
else
    echo "⚠️  Unexpected: Test still failing after fix"
    echo "   This may indicate a deeper structural difference"
    echo "   Manual investigation recommended"
fi

echo "🎯 NEXT STEPS:"
echo "   • Run full test suite: ./api_test_suite.sh"
echo "   • Verify 100% pass rate on ALB consistency test"
echo "   • Ready to proceed to Task 2.1: User registration endpoint"

echo ""
echo "📊 TASK 1.2 COMPLETED"
echo "====================="

# Clean up temporary files
rm -f alb_consistency_test_fix.txt

echo "✅ ALB response consistency fix completed successfully!"
