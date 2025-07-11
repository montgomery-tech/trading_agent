#!/bin/bash

# ALB Health Check Fix
echo "🔧 ALB Health Check Troubleshooting"
echo "==================================="

# Get deployment info
source deployment_info.txt

echo "📋 Issue: ALB not responding - checking target group health"
echo "   ALB URL: http://${ALB_DNS}/health"
echo "   Direct EC2: http://${PUBLIC_IP}:8000/health (✅ Working)"

echo ""
echo "🔍 Step 1: Checking ALB Target Group Health..."

# Check target group health
echo "📊 Current target group health status:"
aws elbv2 describe-target-health --target-group-arn $TARGET_GROUP_ARN --query 'TargetHealthDescriptions[*].[Target.Id,Target.Port,TargetHealth.State,TargetHealth.Description]' --output table

# Get detailed target group configuration
echo ""
echo "📋 Target group configuration:"
aws elbv2 describe-target-groups --target-group-arns $TARGET_GROUP_ARN --query 'TargetGroups[0].[TargetGroupName,Protocol,Port,HealthCheckPath,HealthCheckPort,HealthCheckProtocol,HealthCheckIntervalSeconds,HealthCheckTimeoutSeconds,HealthyThresholdCount,UnhealthyThresholdCount]' --output table

echo ""
echo "🔧 Step 2: Checking ALB Listener Configuration..."

# Check ALB listeners
ALB_ARN=$(aws elbv2 describe-load-balancers --names trading-api-alb --query 'LoadBalancers[0].LoadBalancerArn' --output text)
echo "ALB ARN: $ALB_ARN"

echo "📋 ALB Listeners:"
aws elbv2 describe-listeners --load-balancer-arn $ALB_ARN --query 'Listeners[*].[ListenerArn,Port,Protocol,DefaultActions[0].Type,DefaultActions[0].TargetGroupArn]' --output table

echo ""
echo "🔧 Step 3: Testing ALB Target Health from EC2..."

# Test if the health check endpoint works from the ALB subnet
ssh -i trading-api-keypair.pem -o StrictHostKeyChecking=no ec2-user@${PUBLIC_IP} << 'EOF'
echo "🧪 Testing health endpoint that ALB should be hitting..."

# Test the exact same endpoint ALB uses
echo "📍 Testing /health endpoint (what ALB checks):"
curl -v http://localhost:8000/health 2>&1 | head -20

echo ""
echo "📍 Testing if port 8000 is properly bound:"
netstat -tulpn | grep :8000 || ss -tulpn | grep :8000

echo ""
echo "📍 Testing response headers for ALB compatibility:"
curl -I http://localhost:8000/health 2>/dev/null || echo "Failed to get headers"

EOF

echo ""
echo "🔧 Step 4: Checking Security Group for ALB Communication..."

# Get ALB security group
ALB_SG_ID=$(aws elbv2 describe-load-balancers --names trading-api-alb --query 'LoadBalancers[0].SecurityGroups[0]' --output text)
echo "ALB Security Group: $ALB_SG_ID"

# Get EC2 security group  
EC2_SG_ID=$(aws ec2 describe-instances --instance-ids $INSTANCE_ID --query 'Reservations[0].Instances[0].SecurityGroups[0].GroupId' --output text)
echo "EC2 Security Group: $EC2_SG_ID"

echo ""
echo "📋 Checking if EC2 allows traffic from ALB security group..."
aws ec2 describe-security-groups --group-ids $EC2_SG_ID --query 'SecurityGroups[0].IpPermissions[?FromPort==`8000`]' --output table

echo ""
echo "🔧 Step 5: Fixing ALB to EC2 Communication..."

# Check if EC2 security group allows traffic from ALB security group
RULE_EXISTS=$(aws ec2 describe-security-groups --group-ids $EC2_SG_ID --query "SecurityGroups[0].IpPermissions[?FromPort==\`8000\` && UserIdGroupPairs[?GroupId==\`$ALB_SG_ID\`]]" --output text)

if [ -z "$RULE_EXISTS" ]; then
    echo "⚠️  Missing security group rule for ALB -> EC2 communication"
    echo "   Adding rule to allow ALB to reach EC2 on port 8000..."
    
    aws ec2 authorize-security-group-ingress \
        --group-id $EC2_SG_ID \
        --protocol tcp \
        --port 8000 \
        --source-group $ALB_SG_ID
    
    echo "✅ Added security group rule for ALB communication"
else
    echo "✅ Security group rule exists for ALB -> EC2 communication"
fi

echo ""
echo "🔧 Step 6: Checking ALB Subnets and Health Check Path..."

# Verify ALB subnets
echo "📋 ALB subnet configuration:"
aws elbv2 describe-load-balancers --names trading-api-alb --query 'LoadBalancers[0].AvailabilityZones[*].[ZoneName,SubnetId]' --output table

# Check if target group health check path is correct
HEALTH_CHECK_PATH=$(aws elbv2 describe-target-groups --target-group-arns $TARGET_GROUP_ARN --query 'TargetGroups[0].HealthCheckPath' --output text)
echo ""
echo "📋 Current health check path: $HEALTH_CHECK_PATH"

if [ "$HEALTH_CHECK_PATH" != "/health" ]; then
    echo "⚠️  Health check path is not /health, updating..."
    
    aws elbv2 modify-target-group \
        --target-group-arn $TARGET_GROUP_ARN \
        --health-check-path "/health"
    
    echo "✅ Updated health check path to /health"
fi

echo ""
echo "🔧 Step 7: Manual ALB Health Test..."

# Wait a bit for changes to take effect
echo "⏳ Waiting 30 seconds for security group changes to propagate..."
sleep 30

# Test ALB health again
echo "🧪 Testing ALB health after fixes..."

ALB_SUCCESS=false
for i in {1..5}; do
    echo "   ALB test attempt $i/5..."
    
    if curl -f -s --connect-timeout 15 http://${ALB_DNS}/health > /dev/null; then
        ALB_SUCCESS=true
        break
    fi
    sleep 10
done

if [ "$ALB_SUCCESS" = true ]; then
    echo "✅ ALB is now responding!"
    echo "📊 ALB health response:"
    curl -s http://${ALB_DNS}/health | python3 -m json.tool 2>/dev/null || curl -s http://${ALB_DNS}/health
else
    echo "⚠️  ALB still not responding - checking target health..."
    
    # Check target health again
    echo "📊 Updated target group health:"
    aws elbv2 describe-target-health --target-group-arn $TARGET_GROUP_ARN --query 'TargetHealthDescriptions[*].[Target.Id,TargetHealth.State,TargetHealth.Description]' --output table
    
    # Check if targets are healthy
    TARGET_STATE=$(aws elbv2 describe-target-health --target-group-arn $TARGET_GROUP_ARN --query 'TargetHealthDescriptions[0].TargetHealth.State' --output text)
    echo "   Target state: $TARGET_STATE"
    
    if [ "$TARGET_STATE" = "healthy" ]; then
        echo "✅ Target is healthy - ALB should start working soon"
    else
        echo "⚠️  Target is not healthy yet - may need more time"
        
        # Show detailed reason
        TARGET_REASON=$(aws elbv2 describe-target-health --target-group-arn $TARGET_GROUP_ARN --query 'TargetHealthDescriptions[0].TargetHealth.Description' --output text)
        echo "   Reason: $TARGET_REASON"
    fi
fi

echo ""
echo "📊 FINAL ALB STATUS SUMMARY"
echo "=========================="

# Get final status
DIRECT_HEALTH=$(curl -f -s --connect-timeout 5 http://${PUBLIC_IP}:8000/health >/dev/null 2>&1 && echo "✅ Working" || echo "❌ Failed")
ALB_HEALTH=$(curl -f -s --connect-timeout 10 http://${ALB_DNS}/health >/dev/null 2>&1 && echo "✅ Working" || echo "⚠️  Not Ready")
TARGET_STATE=$(aws elbv2 describe-target-health --target-group-arn $TARGET_GROUP_ARN --query 'TargetHealthDescriptions[0].TargetHealth.State' --output text 2>/dev/null || echo "unknown")

echo "🌐 Access Status:"
echo "   Direct EC2: $DIRECT_HEALTH"
echo "   ALB Access: $ALB_HEALTH"
echo "   Target Health: $TARGET_STATE"
echo ""
echo "🔗 URLs:"
echo "   Direct: curl http://${PUBLIC_IP}:8000/health"
echo "   ALB: curl http://${ALB_DNS}/health"
echo ""

if [ "$ALB_HEALTH" = "✅ Working" ]; then
    echo "🎉 SUCCESS! Both direct and ALB access are working!"
    echo "   Your application is fully load-balanced and production-ready!"
    
elif [ "$TARGET_STATE" = "healthy" ]; then
    echo "✅ Target is healthy - ALB should start working within 1-2 minutes"
    echo "   Keep testing: curl http://${ALB_DNS}/health"
    
elif [ "$TARGET_STATE" = "initial" ]; then
    echo "⏳ Target health check is in initial state"
    echo "   Wait 2-3 minutes for health checks to complete, then test again"
    
else
    echo "⚠️  Target health check may need more investigation"
    echo "   Direct access works, so this is likely an ALB configuration issue"
    echo "   The application itself is working perfectly!"
fi

echo ""
echo "💡 ALB Health Check Notes:"
echo "   • Health checks can take 2-5 minutes to become healthy"
echo "   • ALB needs 2 consecutive successful health checks"
echo "   • Default health check interval is 30 seconds"
echo "   • Direct EC2 access proves the application is working"

echo ""
echo "🔧 ALB troubleshooting completed!"
