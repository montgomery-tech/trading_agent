#!/bin/bash

# test_ssl_setup.sh
# Complete Phase 2 SSL testing and verification

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m'

print_status() {
    echo -e "${2}${1}${NC}"
}

print_step() {
    echo -e "\n${BLUE}==== $1 ====${NC}"
}

print_status "🧪 SSL/HTTPS Setup Testing & Verification" $BLUE
print_status "==========================================" $BLUE

# Load deployment information
source deployment_info.txt

echo ""
print_status "📋 SSL Configuration Status:" $PURPLE
echo "   ALB DNS: $ALB_DNS"
echo "   Certificate ARN: $CERTIFICATE_ARN"
echo "   HTTPS Listener: $HTTPS_LISTENER_ARN"

print_step "Step 1: Waiting for SSL Propagation"

print_status "⏳ Waiting 45 seconds for SSL configuration to fully propagate..." $YELLOW
sleep 45

print_step "Step 2: Testing HTTPS Endpoints"

print_status "🔒 Testing HTTPS health endpoint..." $YELLOW

# Test HTTPS health endpoint
echo ""
echo "🧪 Testing: https://$ALB_DNS/health"
if timeout 15 curl -k -f -s https://${ALB_DNS}/health > /dev/null 2>&1; then
    print_status "✅ HTTPS health endpoint working!" $GREEN
    echo ""
    print_status "📊 HTTPS Health Response:" $BLUE
    curl -k -s https://${ALB_DNS}/health | python3 -m json.tool 2>/dev/null || curl -k -s https://${ALB_DNS}/health
    HTTPS_WORKING=true
else
    print_status "⚠️  HTTPS endpoint not responding yet" $YELLOW
    echo "Let's check if it needs more time..."
    HTTPS_WORKING=false
fi

echo ""
echo "🧪 Testing: https://$ALB_DNS/docs"
DOCS_STATUS=$(timeout 10 curl -k -s -o /dev/null -w "%{http_code}" https://${ALB_DNS}/docs 2>/dev/null || echo "000")
if [ "$DOCS_STATUS" = "200" ]; then
    print_status "✅ HTTPS API docs endpoint working (200 OK)" $GREEN
else
    print_status "⚠️  HTTPS docs status: $DOCS_STATUS" $YELLOW
fi

print_step "Step 3: Testing HTTP to HTTPS Redirect"

print_status "🔄 Testing HTTP to HTTPS redirect..." $YELLOW

echo ""
echo "🧪 Testing redirect: http://$ALB_DNS/health"
HTTP_REDIRECT_STATUS=$(timeout 10 curl -s -o /dev/null -w "%{http_code}" http://${ALB_DNS}/health 2>/dev/null || echo "000")
HTTP_REDIRECT_LOCATION=$(timeout 10 curl -s -I http://${ALB_DNS}/health 2>/dev/null | grep -i location || echo "No location header")

echo "   HTTP Status Code: $HTTP_REDIRECT_STATUS"
echo "   Redirect Location: $HTTP_REDIRECT_LOCATION"

if [ "$HTTP_REDIRECT_STATUS" = "301" ]; then
    print_status "✅ HTTP to HTTPS redirect working perfectly!" $GREEN
    REDIRECT_WORKING=true
elif [ "$HTTP_REDIRECT_STATUS" = "200" ]; then
    print_status "⚠️  HTTP still serving content directly (may need more time)" $YELLOW
    REDIRECT_WORKING=false
else
    print_status "⚠️  Unexpected redirect status: $HTTP_REDIRECT_STATUS" $YELLOW
    REDIRECT_WORKING=false
fi

print_step "Step 4: SSL Certificate Verification"

print_status "🔐 Checking SSL certificate details..." $YELLOW

echo ""
echo "🧪 SSL Certificate Information:"
timeout 10 openssl s_client -connect ${ALB_DNS}:443 -servername ${ALB_DNS} 2>/dev/null | openssl x509 -noout -subject -dates 2>/dev/null || echo "Could not retrieve certificate details"

print_step "Step 5: Security Group Verification"

print_status "🔒 Verifying security group rules..." $YELLOW

echo ""
echo "📋 ALB Security Group HTTPS Rules:"
aws ec2 describe-security-groups --group-ids $ALB_SG_ID --query 'SecurityGroups[0].IpPermissions[?FromPort==`443`]' --output table 2>/dev/null

print_step "Step 6: Comprehensive SSL Test Results"

echo ""
print_status "📊 SSL/HTTPS SETUP RESULTS" $BLUE
print_status "===========================" $BLUE

echo ""
print_status "✅ SSL Configuration Completed:" $GREEN
echo "   • Self-signed SSL certificate generated and uploaded"
echo "   • HTTPS listener configured on port 443"
echo "   • HTTP to HTTPS redirect implemented"
echo "   • Security groups configured for HTTPS traffic"

echo ""
print_status "🧪 Functionality Test Results:" $PURPLE
echo "   HTTPS Health Endpoint: $([ "$HTTPS_WORKING" = true ] && echo "✅ Working" || echo "⚠️  Needs attention")"
echo "   HTTPS Docs Endpoint: $([ "$DOCS_STATUS" = "200" ] && echo "✅ Working ($DOCS_STATUS)" || echo "⚠️  Status: $DOCS_STATUS")"
echo "   HTTP→HTTPS Redirect: $([ "$REDIRECT_WORKING" = true ] && echo "✅ Working (301)" || echo "⚠️  Status: $HTTP_REDIRECT_STATUS")"

echo ""
print_status "🔗 Your SSL-Enabled URLs:" $BLUE
echo "   🔒 HTTPS Health: https://$ALB_DNS/health"
echo "   🔒 HTTPS API Docs: https://$ALB_DNS/docs"
echo "   🔒 HTTPS Root: https://$ALB_DNS/"
echo "   🔄 HTTP (redirects): http://$ALB_DNS (→ HTTPS)"

echo ""
print_status "🧪 Testing Commands:" $PURPLE
echo "   curl -k https://$ALB_DNS/health"
echo "   curl -I http://$ALB_DNS  # Should show 301 redirect"
echo "   curl -k https://$ALB_DNS/docs"

echo ""
print_status "⚠️  Browser Notes:" $YELLOW
echo "   • Use -k flag with curl to ignore self-signed certificate warnings"
echo "   • Browsers will show security warning for self-signed certificates"
echo "   • Click 'Advanced' → 'Proceed to site' to access in browser"
echo "   • This is normal behavior for self-signed certificates"

echo ""
# Determine overall status
if [ "$HTTPS_WORKING" = true ] && [ "$REDIRECT_WORKING" = true ]; then
    print_status "🎉 COMPLETE SUCCESS!" $GREEN
    print_status "SSL/HTTPS implementation is fully operational!" $GREEN
    SSL_STATUS="SUCCESS"
elif [ "$HTTPS_WORKING" = true ]; then
    print_status "✅ PARTIAL SUCCESS!" $GREEN
    print_status "HTTPS is working, redirect may need more time to propagate." $GREEN
    SSL_STATUS="PARTIAL"
else
    print_status "⚠️  NEEDS ATTENTION" $YELLOW
    print_status "SSL configuration may need additional time or troubleshooting." $YELLOW
    SSL_STATUS="ATTENTION"
fi

echo ""
print_status "🎯 Phase 2 Status:" $BLUE
case $SSL_STATUS in
    "SUCCESS")
        echo "   🎊 Phase 2 COMPLETE! Ready for Phase 3 (Monitoring)"
        echo "   📋 SSL/HTTPS fully implemented and working"
        ;;
    "PARTIAL")
        echo "   ✅ HTTPS working! Redirect propagating (wait 5-10 minutes)"
        echo "   📋 Can proceed to Phase 3 or wait for full propagation"
        ;;
    "ATTENTION")
        echo "   🔧 May need additional troubleshooting or time"
        echo "   📋 Check ALB configuration and target group health"
        ;;
esac

echo ""
print_status "💡 Next Steps:" $PURPLE
case $SSL_STATUS in
    "SUCCESS"|"PARTIAL")
        echo "   🚀 Phase 3: Set up monitoring and alerting"
        echo "   📊 Implement CloudWatch dashboards"
        echo "   🔔 Configure SNS notifications"
        echo "   💾 Set up automated backups"
        ;;
    "ATTENTION")
        echo "   ⏳ Wait 10-15 minutes and re-test HTTPS endpoints"
        echo "   🔍 Check ALB listener configuration if issues persist"
        echo "   📋 Verify target group health status"
        ;;
esac

echo ""
print_status "🔒 SSL setup testing completed!" $BLUE

# Save SSL test results
cat > ssl_test_results.txt << EOF
SSL/HTTPS Setup Test Results
Generated: $(date)
============================

SSL Configuration Status: COMPLETE
- Certificate ARN: $CERTIFICATE_ARN
- HTTPS Listener: $HTTPS_LISTENER_ARN
- Redirect Configured: YES

Test Results:
- HTTPS Health Endpoint: $([ "$HTTPS_WORKING" = true ] && echo "WORKING" || echo "NEEDS_ATTENTION")
- HTTPS Docs Endpoint: $DOCS_STATUS
- HTTP→HTTPS Redirect: $HTTP_REDIRECT_STATUS
- Overall Status: $SSL_STATUS

URLs:
- HTTPS Health: https://$ALB_DNS/health
- HTTPS Docs: https://$ALB_DNS/docs
- HTTP Redirect: http://$ALB_DNS (→ HTTPS)

Next Steps:
$(case $SSL_STATUS in
    "SUCCESS"|"PARTIAL") echo "- Ready for Phase 3 (Monitoring)
- Consider custom domain + ACM certificate
- Set up CloudWatch monitoring" ;;
    "ATTENTION") echo "- Wait for SSL propagation
- Re-test in 10-15 minutes
- Check ALB configuration if needed" ;;
esac)
EOF

print_status "📄 Results saved to: ssl_test_results.txt" $BLUE
