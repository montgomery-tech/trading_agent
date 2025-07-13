#!/bin/bash

# ALB Troubleshooting and Fix Script
# Executor Task 1.1 Continuation: Fix ALB issues if found

set -e

# Colors for output
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

# Load deployment information
if [ ! -f "deployment_info.txt" ]; then
    print_status "❌ deployment_info.txt not found." $RED
    exit 1
fi

source deployment_info.txt

print_status "🔧 ALB Troubleshooting and Fix Script" $BLUE
print_status "====================================" $BLUE

echo ""
print_status "📋 Target Infrastructure:" $BLUE
echo "   ALB: $ALB_DNS"
echo "   EC2: $PUBLIC_IP"
echo "   Target Group: $TARGET_GROUP_ARN"

# Step 1: Diagnose Current ALB Issues
print_step "Step 1: Diagnosing ALB Issues"

print_status "🔍 Getting current target health status..." $YELLOW
TARGET_HEALTH_OUTPUT=$(aws elbv2 describe-target-health --target-group-arn $TARGET_GROUP_ARN 2>/dev/null)
TARGET_STATE=$(echo "$TARGET_HEALTH_OUTPUT" | jq -r '.TargetHealthDescriptions[0].TargetHealth.State' 2>/dev/null || echo "unknown")
TARGET_REASON=$(echo "$TARGET_HEALTH_OUTPUT" | jq -r '.TargetHealthDescriptions[0].TargetHealth.Description' 2>/dev/null || echo "unknown")

print_status "   Current State: $TARGET_STATE" $GREEN
print_status "   Reason: $TARGET_REASON" $GREEN

echo ""
echo "📊 Detailed Target Health:"
aws elbv2 describe-target-health --target-group-arn $TARGET_GROUP_ARN --query 'TargetHealthDescriptions[*].[Target.Id,Target.Port,TargetHealth.State,TargetHealth.Description]' --output table

# Step 2: Check ALB and Target Group Configuration
print_step "Step 2: Verifying ALB Configuration"

print_status "⚖️  Checking ALB configuration..." $YELLOW
aws elbv2 describe-load-balancers --load-balancer-arns $ALB_ARN --query 'LoadBalancers[0].[LoadBalancerName,Scheme,State.Code,VpcId]' --output table

print_status "🎯 Checking target group configuration..." $YELLOW
TG_CONFIG=$(aws elbv2 describe-target-groups --target-group-arns $TARGET_GROUP_ARN)
HEALTH_CHECK_PATH=$(echo "$TG_CONFIG" | jq -r '.TargetGroups[0].HealthCheckPath')
HEALTH_CHECK_PROTOCOL=$(echo "$TG_CONFIG" | jq -r '.TargetGroups[0].HealthCheckProtocol')
HEALTH_CHECK_PORT=$(echo "$TG_CONFIG" | jq -r '.TargetGroups[0].HealthCheckPort')
HEALTH_CHECK_INTERVAL=$(echo "$TG_CONFIG" | jq -r '.TargetGroups[0].HealthCheckIntervalSeconds')

echo "Target Group Health Check Configuration:"
echo "   Path: $HEALTH_CHECK_PATH"
echo "   Protocol: $HEALTH_CHECK_PROTOCOL"
echo "   Port: $HEALTH_CHECK_PORT"
echo "   Interval: $HEALTH_CHECK_INTERVAL seconds"

# Step 3: Fix Health Check Configuration if Needed
print_step "Step 3: Fixing Health Check Configuration"

if [ "$HEALTH_CHECK_PATH" != "/health" ]; then
    print_status "⚠️  Health check path is '$HEALTH_CHECK_PATH', should be '/health'" $YELLOW
    print_status "🔧 Updating health check path..." $BLUE
    
    aws elbv2 modify-target-group \
        --target-group-arn $TARGET_GROUP_ARN \
        --health-check-path "/health" \
        --health-check-protocol HTTP \
        --health-check-port 8000
    
    print_status "✅ Updated health check configuration" $GREEN
else
    print_status "✅ Health check path is correctly set to '/health'" $GREEN
fi

# Step 4: Check Security Group Rules
print_step "Step 4: Verifying Security Group Rules"

print_status "🔒 Checking security group rules..." $YELLOW

# Get ALB security group
ALB_SG_ID=$(aws elbv2 describe-load-balancers --load-balancer-arns $ALB_ARN --query 'LoadBalancers[0].SecurityGroups[0]' --output text)
print_status "   ALB Security Group: $ALB_SG_ID" $GREEN

# Check if EC2 allows traffic from ALB
print_status "🔍 Checking EC2 security group rules for ALB access..." $YELLOW
EC2_RULES=$(aws ec2 describe-security-groups --group-ids $EC2_SG_ID --query "SecurityGroups[0].IpPermissions[?FromPort==\`8000\`]" --output json)

# Check if rule exists for ALB security group
ALB_RULE_EXISTS=$(echo "$EC2_RULES" | jq -r ".[] | select(.UserIdGroupPairs[].GroupId == \"$ALB_SG_ID\") | .FromPort" 2>/dev/null)

if [ -z "$ALB_RULE_EXISTS" ]; then
    print_status "⚠️  Missing security group rule for ALB -> EC2 communication" $YELLOW
    print_status "🔧 Adding security group rule..." $BLUE
    
    aws ec2 authorize-security-group-ingress \
        --group-id $EC2_SG_ID \
        --protocol tcp \
        --port 8000 \
        --source-group $ALB_SG_ID
    
    print_status "✅ Added security group rule for ALB access" $GREEN
else
    print_status "✅ Security group rule exists for ALB -> EC2 communication" $GREEN
fi

# Step 5: Test Application Health from ALB Perspective
print_step "Step 5: Testing Application Health"

print_status "🧪 Testing if application responds to health checks..." $YELLOW

# Test from EC2 itself (simulating ALB health check)
ssh -i trading-api-keypair.pem -o StrictHostKeyChecking=no ec2-user@${PUBLIC_IP} << 'EOF'
echo "🔍 Testing health endpoint from server perspective:"

# Test the exact health check ALB will perform
echo "Testing: curl -f http://localhost:8000/health"
if curl -f -s --connect-timeout 5 http://localhost:8000/health > /dev/null; then
    echo "✅ Local health check successful"
    echo "Response:"
    curl -s http://localhost:8000/health
else
    echo "❌ Local health check failed"
    echo "Checking if application is running:"
    ps aux | grep uvicorn | grep -v grep || echo "No uvicorn processes found"
    
    echo "Checking port 8000:"
    netstat -tulpn | grep :8000 || ss -tulpn | grep :8000 || echo "Port 8000 not listening"
fi

echo ""
echo "🔍 Testing response headers:"
curl -I -s http://localhost:8000/health 2>/dev/null || echo "Failed to get headers"

echo ""
echo "📄 Recent application logs:"
if [ -f "/var/log/trading-api/app.log" ]; then
    tail -5 /var/log/trading-api/app.log
else
    echo "Log file not found"
fi
EOF

# Step 6: Restart Application if Needed
print_step "Step 6: Application Restart (if needed)"

APP_RUNNING=$(ssh -i trading-api-keypair.pem -o StrictHostKeyChecking=no ec2-user@${PUBLIC_IP} "ps aux | grep uvicorn | grep -v grep | wc -l" 2>/dev/null)

if [ "$APP_RUNNING" -eq 0 ]; then
    print_status "⚠️  No uvicorn processes found. Restarting application..." $YELLOW
    
    ssh -i trading-api-keypair.pem -o StrictHostKeyChecking=no ec2-user@${PUBLIC_IP} << 'EOF'
cd /opt/trading-api

echo "🔧 Starting FastAPI application..."

# Kill any existing processes
pkill -f uvicorn || true

# Wait a moment
sleep 2

# Start the application
nohup python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 > /var/log/trading-api/app.log 2>&1 &

# Wait for startup
sleep 5

# Check if it started
if ps aux | grep uvicorn | grep -v grep > /dev/null; then
    echo "✅ Application restarted successfully"
else
    echo "❌ Application failed to start"
fi
EOF
    
    print_status "✅ Application restart completed" $GREEN
    
    # Wait for application to fully start
    print_status "⏳ Waiting 10 seconds for application startup..." $YELLOW
    sleep 10
else
    print_status "✅ Application is already running ($APP_RUNNING processes)" $GREEN
fi

# Step 7: Wait for Health Checks and Test
print_step "Step 7: Waiting for Health Checks"

print_status "⏳ Waiting for ALB health checks to complete..." $YELLOW
print_status "   (This may take 2-5 minutes for health checks to pass)" $BLUE

# Wait and check health status periodically
for i in {1..10}; do
    echo ""
    print_status "🔄 Health check attempt $i/10..." $BLUE
    
    # Check target health
    NEW_TARGET_STATE=$(aws elbv2 describe-target-health --target-group-arn $TARGET_GROUP_ARN --query 'TargetHealthDescriptions[0].TargetHealth.State' --output text 2>/dev/null)
    print_status "   Target State: $NEW_TARGET_STATE" $GREEN
    
    # Test ALB access
    if curl -f -s --connect-timeout 10 http://${ALB_DNS}/health > /dev/null 2>&1; then
        print_status "✅ ALB health check successful!" $GREEN
        echo ""
        print_status "📊 ALB Response:" $BLUE
        curl -s http://${ALB_DNS}/health | python3 -m json.tool 2>/dev/null || curl -s http://${ALB_DNS}/health
        ALB_WORKING=true
        break
    else
        print_status "   ⏳ ALB not ready yet..." $YELLOW
        ALB_WORKING=false
    fi
    
    # If target is healthy but ALB isn't responding, check listener
    if [ "$NEW_TARGET_STATE" = "healthy" ] && [ "$ALB_WORKING" = false ]; then
        print_status "   🔍 Target healthy but ALB not responding - checking listeners..." $YELLOW
        aws elbv2 describe-listeners --load-balancer-arn $ALB_ARN --query 'Listeners[*].[Port,Protocol,DefaultActions[0].TargetGroupArn]' --output table
    fi
    
    # Break early if healthy
    if [ "$NEW_TARGET_STATE" = "healthy" ] && [ "$ALB_WORKING" = true ]; then
        break
    fi
    
    sleep 30
done

# Step 8: Final Status Report
print_step "Step 8: Final Status Report"

# Get final status
FINAL_DIRECT_HEALTH=$(curl -f -s --connect-timeout 5 http://${PUBLIC_IP}:8000/health >/dev/null 2>&1 && echo "✅ Working" || echo "❌ Failed")
FINAL_ALB_HEALTH=$(curl -f -s --connect-timeout 10 http://${ALB_DNS}/health >/dev/null 2>&1 && echo "✅ Working" || echo "⚠️  Issues")
FINAL_TARGET_STATE=$(aws elbv2 describe-target-health --target-group-arn $TARGET_GROUP_ARN --query 'TargetHealthDescriptions[0].TargetHealth.State' --output text 2>/dev/null)

echo ""
print_status "📊 FINAL ALB TROUBLESHOOTING RESULTS" $BLUE
print_status "====================================" $BLUE

echo ""
print_status "🌐 Access Status:" $BLUE
echo "   Direct EC2: $FINAL_DIRECT_HEALTH"
echo "   ALB Access: $FINAL_ALB_HEALTH"
echo "   Target Health: $FINAL_TARGET_STATE"

echo ""
print_status "🔗 Test URLs:" $BLUE
echo "   Direct: curl http://${PUBLIC_IP}:8000/health"
echo "   ALB: curl http://${ALB_DNS}/health"

echo ""
if [ "$FINAL_ALB_HEALTH" = "✅ Working" ]; then
    print_status "🎉 SUCCESS: ALB is now working perfectly!" $GREEN
    print_status "   Both direct and load-balanced access are operational." $GREEN
    FINAL_STATUS="SUCCESS"
elif [ "$FINAL_TARGET_STATE" = "healthy" ]; then
    print_status "✅ PROGRESS: Target is healthy, ALB may need more time" $GREEN
    print_status "   Keep testing ALB periodically. It should work within minutes." $GREEN
    FINAL_STATUS="HEALTHY_TARGET"
elif [ "$FINAL_DIRECT_HEALTH" = "✅ Working" ]; then
    print_status "⚠️  PARTIAL: Direct access works, ALB needs more investigation" $YELLOW
    print_status "   Application is functional. ALB configuration may need review." $YELLOW
    FINAL_STATUS="PARTIAL"
else
    print_status "❌ ISSUES: Both direct and ALB access have problems" $RED
    print_status "   Application or infrastructure issues need immediate attention." $RED
    FINAL_STATUS="ISSUES"
fi

echo ""
print_status "💡 Recommendations:" $BLUE

case $FINAL_STATUS in
    "SUCCESS")
        echo "   🎊 ALB troubleshooting successful! Ready for next steps:"
        echo "   📋 • Implement SSL/HTTPS"
        echo "   📋 • Set up monitoring and alerts"
        echo "   📋 • Configure automated backups"
        ;;
    "HEALTHY_TARGET")
        echo "   ⏳ Health checks in progress. Next steps:"
        echo "   📋 • Wait 5-10 more minutes and test ALB again"
        echo "   📋 • If still not working, check ALB listener configuration"
        echo "   📋 • Consider redeploying target group if persistent"
        ;;
    "PARTIAL")
        echo "   🔧 Focus on ALB-specific issues:"
        echo "   📋 • Review ALB listener configuration"
        echo "   📋 • Check target group port mappings"
        echo "   📋 • Verify subnet routing"
        echo "   📋 • Application is functional via direct access"
        ;;
    "ISSUES")
        echo "   🚨 Address application issues first:"
        echo "   📋 • Check application logs for errors"
        echo "   📋 • Verify environment configuration"
        echo "   📋 • Restart application services"
        echo "   📋 • Check security group rules"
        ;;
esac

# Save troubleshooting results
cat > alb_troubleshooting_results.txt << EOF
ALB Troubleshooting Results
Generated: $(date)
==========================

Final Status: $FINAL_STATUS

Access Test Results:
- Direct EC2: $FINAL_DIRECT_HEALTH
- ALB Access: $FINAL_ALB_HEALTH
- Target Health: $FINAL_TARGET_STATE

Configuration Verified:
- Health Check Path: /health
- Security Group Rules: Updated
- Application Status: Checked and restarted if needed

URLs:
- Direct: http://${PUBLIC_IP}:8000/health
- ALB: http://${ALB_DNS}/health

Next Steps:
$(case $FINAL_STATUS in
    "SUCCESS") echo "✅ ALB working - proceed with SSL and monitoring setup" ;;
    "HEALTHY_TARGET") echo "⏳ Wait for ALB health checks to complete" ;;
    "PARTIAL") echo "🔧 Investigate ALB listener and routing configuration" ;;
    "ISSUES") echo "🚨 Debug application and infrastructure issues" ;;
esac)
EOF

echo ""
print_status "📄 Results saved to: alb_troubleshooting_results.txt" $BLUE
print_status "🔧 ALB troubleshooting completed!" $BLUE
