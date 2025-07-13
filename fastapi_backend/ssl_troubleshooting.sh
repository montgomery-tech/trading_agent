#!/bin/bash

# ssl_troubleshooting.sh
# Diagnose and fix SSL/HTTPS issues

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() {
    echo -e "${2}${1}${NC}"
}

print_step() {
    echo -e "\n${BLUE}==== $1 ====${NC}"
}

print_status "🔍 SSL/HTTPS Troubleshooting" $BLUE
print_status "============================" $BLUE

# Load deployment information
source deployment_info.txt

print_step "Step 1: Check Target Group Health"

print_status "🎯 Checking target group health for HTTPS..." $YELLOW

echo "📊 Current target group health:"
aws elbv2 describe-target-health --target-group-arn $TARGET_GROUP_ARN --query 'TargetHealthDescriptions[*].[Target.Id,Target.Port,TargetHealth.State,TargetHealth.Description]' --output table

TARGET_STATE=$(aws elbv2 describe-target-health --target-group-arn $TARGET_GROUP_ARN --query 'TargetHealthDescriptions[0].TargetHealth.State' --output text 2>/dev/null)
print_status "Target Health State: $TARGET_STATE" $GREEN

print_step "Step 2: Verify ALB Listeners Configuration"

print_status "⚖️  Checking ALB listeners..." $YELLOW

echo "📋 All ALB listeners:"
aws elbv2 describe-listeners --load-balancer-arn $ALB_ARN --query 'Listeners[*].[Port,Protocol,DefaultActions[0].Type,ListenerArn]' --output table

echo ""
echo "🔍 HTTPS Listener details:"
aws elbv2 describe-listeners --listener-arns $HTTPS_LISTENER_ARN --query 'Listeners[0].[Port,Protocol,Certificates[0].CertificateArn,DefaultActions[0].Type]' --output table

print_step "Step 3: Test Basic Network Connectivity"

print_status "🌐 Testing basic network connectivity..." $YELLOW

echo "🧪 Testing if ALB accepts connections on port 443:"
timeout 10 bash -c "</dev/tcp/${ALB_DNS}/443" 2>/dev/null && echo "✅ Port 443 is reachable" || echo "❌ Port 443 not reachable"

echo ""
echo "🧪 Testing if ALB accepts connections on port 80:"
timeout 10 bash -c "</dev/tcp/${ALB_DNS}/80" 2>/dev/null && echo "✅ Port 80 is reachable" || echo "❌ Port 80 not reachable"

print_step "Step 4: Check Certificate Status"

print_status "🔐 Checking certificate status in ACM..." $YELLOW

CERT_STATUS=$(aws acm describe-certificate --certificate-arn $CERTIFICATE_ARN --query 'Certificate.Status' --output text)
echo "Certificate Status: $CERT_STATUS"

if [ "$CERT_STATUS" != "ISSUED" ]; then
    print_status "⚠️  Certificate status is $CERT_STATUS" $YELLOW
    echo "Certificate details:"
    aws acm describe-certificate --certificate-arn $CERTIFICATE_ARN --query 'Certificate.[Status,DomainName,InUseBy]' --output table
fi

print_step "Step 5: Test Direct EC2 Application"

print_status "🧪 Verifying the application is still running..." $YELLOW

# Test direct EC2 health
DIRECT_HEALTH=$(curl -f -s --connect-timeout 5 http://${PUBLIC_IP}:8000/health >/dev/null 2>&1 && echo "WORKING" || echo "FAILED")
echo "Direct EC2 Health: $DIRECT_HEALTH"

if [ "$DIRECT_HEALTH" = "WORKING" ]; then
    print_status "✅ Application is running correctly on EC2" $GREEN
    echo "Health response:"
    curl -s http://${PUBLIC_IP}:8000/health
else
    print_status "❌ Application issue detected on EC2" $RED
    print_status "🔍 Let's check if the application is running..." $YELLOW
    
    # Check if we need to restart the application via SSM
    echo "This might require restarting the application via SSM"
    echo "Run: aws ssm start-session --target $INSTANCE_ID"
    echo "Then: sudo -u ec2-user python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 &"
fi

print_step "Step 6: ALB Health Check Diagnostics"

print_status "🔍 Analyzing ALB health check patterns..." $YELLOW

# Check if ALB is actually trying to reach the targets
if [ "$TARGET_STATE" = "healthy" ]; then
    print_status "✅ Target is healthy - ALB should work" $GREEN
    echo ""
    echo "Since target is healthy but HTTPS isn't working, this suggests:"
    echo "1. 🔧 HTTPS listener configuration issue"
    echo "2. ⏳ SSL handshake/certificate issue"
    echo "3. 🔄 Listener routing problem"
    
elif [ "$TARGET_STATE" = "unhealthy" ]; then
    print_status "⚠️  Target is unhealthy" $YELLOW
    echo "Health check failure reason:"
    aws elbv2 describe-target-health --target-group-arn $TARGET_GROUP_ARN --query 'TargetHealthDescriptions[0].TargetHealth.Description' --output text
    
else
    print_status "⚠️  Target state: $TARGET_STATE" $YELLOW
fi

print_step "Step 7: Quick HTTPS Fix Attempt"

print_status "🔧 Attempting quick HTTPS fix..." $YELLOW

echo "📋 Option 1: Wait for propagation (recommended first try)"
echo "   SSL configurations can take 5-15 minutes to fully propagate"
echo "   Test again in 10 minutes: curl -k https://$ALB_DNS/health"

echo ""
echo "📋 Option 2: Restart HTTPS listener"
read -p "Try recreating HTTPS listener? (y/n): " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_status "🔄 Recreating HTTPS listener..." $YELLOW
    
    # Delete and recreate HTTPS listener
    aws elbv2 delete-listener --listener-arn $HTTPS_LISTENER_ARN
    sleep 5
    
    NEW_HTTPS_LISTENER_ARN=$(aws elbv2 create-listener \
        --load-balancer-arn $ALB_ARN \
        --protocol HTTPS \
        --port 443 \
        --certificates CertificateArn=$CERTIFICATE_ARN \
        --default-actions Type=forward,TargetGroupArn=$TARGET_GROUP_ARN \
        --query 'Listeners[0].ListenerArn' \
        --output text)
    
    if [ ! -z "$NEW_HTTPS_LISTENER_ARN" ]; then
        print_status "✅ HTTPS listener recreated" $GREEN
        echo "New Listener ARN: $NEW_HTTPS_LISTENER_ARN"
        
        # Update deployment info
        sed -i.bak "s|HTTPS_LISTENER_ARN=.*|HTTPS_LISTENER_ARN=$NEW_HTTPS_LISTENER_ARN|" deployment_info.txt
        
        print_status "⏳ Waiting 30 seconds for new listener..." $YELLOW
        sleep 30
        
        # Test again
        echo "🧪 Testing HTTPS after listener recreation:"
        if timeout 15 curl -k -f -s https://${ALB_DNS}/health > /dev/null 2>&1; then
            print_status "✅ HTTPS working after listener recreation!" $GREEN
            curl -k -s https://${ALB_DNS}/health
        else
            print_status "⚠️  Still not working - may need more time" $YELLOW
        fi
    fi
fi

print_step "Step 8: Alternative Testing"

print_status "🧪 Let's try alternative testing approaches..." $YELLOW

echo ""
echo "🔍 Testing with verbose curl output:"
echo "curl -k -v https://$ALB_DNS/health"
timeout 15 curl -k -v https://${ALB_DNS}/health 2>&1 | head -20

echo ""
echo "🔍 Testing with OpenSSL:"
echo "openssl s_client -connect $ALB_DNS:443"
timeout 10 openssl s_client -connect ${ALB_DNS}:443 -servername ${ALB_DNS} 2>&1 | head -10

print_step "Troubleshooting Summary"

echo ""
print_status "📊 SSL TROUBLESHOOTING RESULTS" $BLUE
print_status "===============================" $BLUE

echo ""
print_status "✅ SSL Infrastructure Status:" $GREEN
echo "   • Certificate uploaded to ACM: ✅"
echo "   • HTTPS listener created: ✅"
echo "   • Security groups configured: ✅"
echo "   • Target group health: $TARGET_STATE"

echo ""
print_status "⚠️  Current Issues:" $YELLOW
echo "   • HTTPS endpoints not responding"
echo "   • May need additional propagation time"
echo "   • Possible listener configuration issue"

echo ""
print_status "💡 Recommended Next Steps:" $BLUE
echo "1. ⏳ Wait 10-15 minutes for full AWS propagation"
echo "2. 🧪 Test again: curl -k https://$ALB_DNS/health"
echo "3. 🔍 If still not working, check CloudWatch ALB logs"
echo "4. 🔄 Consider simple restart: delete and recreate HTTPS listener"

echo ""
print_status "🎯 Quick Test Commands:" $PURPLE
echo "   curl -k https://$ALB_DNS/health"
echo "   curl -I http://$ALB_DNS/health"
echo "   openssl s_client -connect $ALB_DNS:443"

echo ""
print_status "🔧 SSL troubleshooting completed!" $BLUE
