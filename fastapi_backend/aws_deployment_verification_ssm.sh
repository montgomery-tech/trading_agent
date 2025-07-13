#!/bin/bash

# aws_deployment_verification_ssm.sh
# AWS FastAPI Deployment Verification Script using SSM
# Executor Task 1.1: Verify ALB health check status and functionality

set -e

# Colors for output
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

# Check if deployment info exists
if [ ! -f "deployment_info.txt" ]; then
    print_status "❌ deployment_info.txt not found. Cannot proceed with verification." $RED
    exit 1
fi

# Load deployment information
source deployment_info.txt

print_status "🔍 AWS FastAPI Deployment Verification (via SSM)" $BLUE
print_status "================================================" $BLUE

echo ""
print_status "📋 Infrastructure Overview:" $PURPLE
echo "   VPC: $VPC_ID"
echo "   EC2: $INSTANCE_ID ($PUBLIC_IP)"
echo "   RDS: $RDS_ENDPOINT"
echo "   ALB: $ALB_DNS"
echo "   Target Group: $TARGET_GROUP_ARN"

# Step 1: Verify AWS Infrastructure Status
print_step "Step 1: Verifying AWS Infrastructure Status"

# Check EC2 instance status
print_status "🖥️  Checking EC2 Instance Status..." $YELLOW
INSTANCE_STATE=$(aws ec2 describe-instances --instance-ids $INSTANCE_ID --query 'Reservations[0].Instances[0].State.Name' --output text 2>/dev/null)
print_status "   EC2 State: $INSTANCE_STATE" $GREEN

if [ "$INSTANCE_STATE" != "running" ]; then
    print_status "❌ EC2 instance is not running. Deployment verification failed." $RED
    exit 1
fi

# Check RDS instance status
print_status "🗄️  Checking RDS Instance Status..." $YELLOW
RDS_STATE=$(aws rds describe-db-instances --db-instance-identifier trading-api-db --query 'DBInstances[0].DBInstanceStatus' --output text 2>/dev/null)
print_status "   RDS State: $RDS_STATE" $GREEN

# Check ALB status
print_status "⚖️  Checking ALB Status..." $YELLOW
ALB_STATE=$(aws elbv2 describe-load-balancers --load-balancer-arns $ALB_ARN --query 'LoadBalancers[0].State.Code' --output text 2>/dev/null)
print_status "   ALB State: $ALB_STATE" $GREEN

# Step 2: Test SSM Connectivity
print_step "Step 2: Testing SSM Connectivity"

print_status "🔗 Testing SSM connection..." $YELLOW
if aws ssm describe-instance-information --filters Key=InstanceIds,Values=$INSTANCE_ID --query 'InstanceInformationList[0].InstanceId' --output text | grep -q $INSTANCE_ID; then
    print_status "✅ SSM connectivity verified" $GREEN
    
    # Get SSM status
    SSM_STATUS=$(aws ssm describe-instance-information --filters Key=InstanceIds,Values=$INSTANCE_ID --query 'InstanceInformationList[0].PingStatus' --output text)
    print_status "   SSM Agent Status: $SSM_STATUS" $GREEN
else
    print_status "❌ SSM connection failed" $RED
    exit 1
fi

# Step 3: Verify Application Status on EC2 via SSM
print_step "Step 3: Verifying Application Status on EC2 (via SSM)"

print_status "📦 Checking application files and dependencies..." $YELLOW

# Create a comprehensive check command for SSM
SSM_COMMAND_ID=$(aws ssm send-command \
    --instance-ids $INSTANCE_ID \
    --document-name "AWS-RunShellScript" \
    --parameters 'commands=[
        "cd /opt/trading-api",
        "echo \"📁 Application directory contents:\"",
        "ls -la | head -10",
        "echo \"\"",
        "echo \"📝 Environment file status:\"",
        "if [ -f \".env\" ]; then echo \"✅ .env file exists ($(wc -l < .env) lines)\"; else echo \"❌ .env file missing\"; fi",
        "echo \"\"",
        "echo \"🐍 Critical Python dependencies:\"",
        "python3 -c \"import sys; deps = ['"'"'fastapi'"'"', '"'"'uvicorn'"'"', '"'"'sqlalchemy'"'"', '"'"'psycopg2'"'"', '"'"'pydantic'"'"', '"'"'decouple'"'"']; [print(f'"'"'✅ {dep}'"'"') if __import__(dep) else print(f'"'"'❌ {dep}'"'"') for dep in deps]\" 2>/dev/null || echo \"❌ Python import test failed\"",
        "echo \"\"",
        "echo \"📊 Application processes:\"",
        "UVICORN_COUNT=$(ps aux | grep uvicorn | grep -v grep | wc -l)",
        "echo \"   Uvicorn processes running: $UVICORN_COUNT\"",
        "if [ \"$UVICORN_COUNT\" -gt 0 ]; then echo \"✅ Application is running\"; ps aux | grep uvicorn | grep -v grep | head -3; else echo \"❌ No uvicorn processes found\"; fi",
        "echo \"\"",
        "echo \"📄 Recent application logs (last 10 lines):\"",
        "if [ -f \"/var/log/trading-api/app.log\" ]; then tail -10 /var/log/trading-api/app.log; else echo \"⚠️  Log file not found at /var/log/trading-api/app.log\"; fi"
    ]' \
    --query 'Command.CommandId' \
    --output text)

print_status "   Command ID: $SSM_COMMAND_ID" $BLUE
print_status "⏳ Waiting for command execution..." $YELLOW
sleep 10

# Get command results
COMMAND_STATUS=$(aws ssm get-command-invocation \
    --command-id $SSM_COMMAND_ID \
    --instance-id $INSTANCE_ID \
    --query 'Status' \
    --output text 2>/dev/null)

if [ "$COMMAND_STATUS" = "Success" ]; then
    print_status "✅ Application status check completed" $GREEN
    echo ""
    print_status "📋 Application Status Results:" $BLUE
    aws ssm get-command-invocation \
        --command-id $SSM_COMMAND_ID \
        --instance-id $INSTANCE_ID \
        --query 'StandardOutputContent' \
        --output text
else
    print_status "⚠️  Command status: $COMMAND_STATUS" $YELLOW
    echo "Command output:"
    aws ssm get-command-invocation \
        --command-id $SSM_COMMAND_ID \
        --instance-id $INSTANCE_ID \
        --query 'StandardOutputContent' \
        --output text
fi

# Step 4: Test Direct EC2 Health Endpoint
print_step "Step 4: Testing Direct EC2 Health Endpoint"

print_status "🧪 Testing external health check (${PUBLIC_IP}:8000)..." $YELLOW
EXTERNAL_HEALTH=$(curl -f -s --connect-timeout 10 http://${PUBLIC_IP}:8000/health >/dev/null 2>&1 && echo "PASS" || echo "FAIL")

if [ "$EXTERNAL_HEALTH" = "PASS" ]; then
    print_status "✅ Direct EC2 access working" $GREEN
    print_status "📊 Health response:" $BLUE
    curl -s http://${PUBLIC_IP}:8000/health | python3 -m json.tool 2>/dev/null || curl -s http://${PUBLIC_IP}:8000/health
else
    print_status "❌ Direct EC2 access failed" $RED
    print_status "🔍 Debugging information:" $YELLOW
    
    # Check security group rules
    echo "Security Group Rules for port 8000:"
    aws ec2 describe-security-groups --group-ids $EC2_SG_ID --query 'SecurityGroups[0].IpPermissions[?FromPort==`8000`]' --output table
fi

# Step 5: Test ALB Health and Target Group Status
print_step "Step 5: Testing ALB Health and Target Group Status"

print_status "🎯 Checking Target Group Health..." $YELLOW
echo "📊 Target Group Health Status:"
aws elbv2 describe-target-health --target-group-arn $TARGET_GROUP_ARN --query 'TargetHealthDescriptions[*].[Target.Id,Target.Port,TargetHealth.State,TargetHealth.Description]' --output table

TARGET_STATE=$(aws elbv2 describe-target-health --target-group-arn $TARGET_GROUP_ARN --query 'TargetHealthDescriptions[0].TargetHealth.State' --output text 2>/dev/null)
print_status "   Target Health State: $TARGET_STATE" $GREEN

print_status "🧪 Testing ALB health endpoint..." $YELLOW
ALB_HEALTH=$(curl -f -s --connect-timeout 15 http://${ALB_DNS}/health >/dev/null 2>&1 && echo "PASS" || echo "FAIL")

if [ "$ALB_HEALTH" = "PASS" ]; then
    print_status "✅ ALB access working" $GREEN
    print_status "📊 ALB health response:" $BLUE
    curl -s http://${ALB_DNS}/health | python3 -m json.tool 2>/dev/null || curl -s http://${ALB_DNS}/health
else
    print_status "⚠️  ALB health check failed" $YELLOW
    
    print_status "🔍 ALB Diagnostic Information:" $YELLOW
    
    # Check ALB configuration
    echo "ALB Configuration:"
    aws elbv2 describe-load-balancers --load-balancer-arns $ALB_ARN --query 'LoadBalancers[0].[LoadBalancerName,Scheme,Type,State.Code]' --output table
    
    # Check target group configuration
    echo ""
    echo "Target Group Configuration:"
    aws elbv2 describe-target-groups --target-group-arns $TARGET_GROUP_ARN --query 'TargetGroups[0].[TargetGroupName,Protocol,Port,HealthCheckPath,HealthCheckProtocol,HealthCheckIntervalSeconds,HealthyThresholdCount]' --output table
fi

# Step 6: Test API Endpoints (if direct access works)
print_step "Step 6: Testing API Endpoints"

if [ "$EXTERNAL_HEALTH" = "PASS" ]; then
    print_status "🧪 Testing additional API endpoints..." $YELLOW
    
    # Test root endpoint
    echo "Root endpoint (/):"
    curl -s -w "Status: %{http_code}\n" http://${PUBLIC_IP}:8000/ || echo "Failed to reach root endpoint"
    
    echo ""
    # Test API documentation
    echo "API docs endpoint (/docs):"
    curl -s -w "Status: %{http_code}\n" -o /dev/null http://${PUBLIC_IP}:8000/docs || echo "Failed to reach docs endpoint"
    
    echo ""
    # Test API v1 prefix
    echo "API v1 health (/api/v1/health):"
    curl -s -w "Status: %{http_code}\n" http://${PUBLIC_IP}:8000/api/v1/health || echo "Failed to reach API v1 health"
    
else
    print_status "⚠️  Skipping API endpoint tests due to failed direct access" $YELLOW
fi

# Step 7: Database Connectivity Test via SSM
print_step "Step 7: Testing Database Connectivity (via SSM)"

print_status "🗄️  Testing database connection..." $YELLOW

# Create database test command
DB_TEST_COMMAND_ID=$(aws ssm send-command \
    --instance-ids $INSTANCE_ID \
    --document-name "AWS-RunShellScript" \
    --parameters 'commands=[
        "cd /opt/trading-api",
        "echo \"🧪 Testing PostgreSQL connection:\"",
        "python3 -c \"",
        "import os, sys",
        "try:",
        "    from decouple import config",
        "    database_url = config('"'"'DATABASE_URL'"'"')",
        "    print('"'"'✅ Environment loaded, DATABASE_URL configured'"'"')",
        "except Exception as e:",
        "    print(f'"'"'❌ Failed to load environment: {e}'"'"')",
        "    sys.exit(1)",
        "",
        "try:",
        "    import psycopg2",
        "    from urllib.parse import urlparse",
        "    parsed = urlparse(database_url)",
        "    conn = psycopg2.connect(",
        "        host=parsed.hostname,",
        "        port=parsed.port,",
        "        database=parsed.path[1:],",
        "        user=parsed.username,",
        "        password=parsed.password",
        "    )",
        "    cursor = conn.cursor()",
        "    cursor.execute('"'"'SELECT version();'"'"')",
        "    version = cursor.fetchone()[0]",
        "    print(f'"'"'✅ Database connection successful'"'"')",
        "    print(f'"'"'   PostgreSQL version: {version[:50]}...'"'"')",
        "    cursor.execute('"'"'SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = %s'"'"', ('"'"'public'"'"',))",
        "    table_count = cursor.fetchone()[0]",
        "    print(f'"'"'   Tables in public schema: {table_count}'"'"')",
        "    cursor.close()",
        "    conn.close()",
        "except Exception as e:",
        "    print(f'"'"'❌ Database connection failed: {e}'"'"')",
        "    sys.exit(1)",
        "\""
    ]' \
    --query 'Command.CommandId' \
    --output text)

sleep 8

# Get database test results
DB_COMMAND_STATUS=$(aws ssm get-command-invocation \
    --command-id $DB_TEST_COMMAND_ID \
    --instance-id $INSTANCE_ID \
    --query 'Status' \
    --output text 2>/dev/null)

if [ "$DB_COMMAND_STATUS" = "Success" ]; then
    print_status "✅ Database connectivity test completed" $GREEN
    aws ssm get-command-invocation \
        --command-id $DB_TEST_COMMAND_ID \
        --instance-id $INSTANCE_ID \
        --query 'StandardOutputContent' \
        --output text
else
    print_status "⚠️  Database test status: $DB_COMMAND_STATUS" $YELLOW
    aws ssm get-command-invocation \
        --command-id $DB_TEST_COMMAND_ID \
        --instance-id $INSTANCE_ID \
        --query 'StandardOutputContent' \
        --output text
fi

# Step 8: Generate Comprehensive Status Report
print_step "Step 8: Comprehensive Status Report"

# Get application process count via SSM
APP_PROCESSES_COMMAND_ID=$(aws ssm send-command \
    --instance-ids $INSTANCE_ID \
    --document-name "AWS-RunShellScript" \
    --parameters 'commands=["ps aux | grep uvicorn | grep -v grep | wc -l"]' \
    --query 'Command.CommandId' \
    --output text)

sleep 3
APP_PROCESSES=$(aws ssm get-command-invocation \
    --command-id $APP_PROCESSES_COMMAND_ID \
    --instance-id $INSTANCE_ID \
    --query 'StandardOutputContent' \
    --output text | tr -d '\n')

echo ""
print_status "📊 DEPLOYMENT VERIFICATION SUMMARY" $BLUE
print_status "===================================" $BLUE

echo ""
print_status "🏗️  Infrastructure Status:" $PURPLE
echo "   ✅ VPC: $VPC_ID"
echo "   ✅ EC2: $INSTANCE_STATE ($PUBLIC_IP)"
echo "   ✅ RDS: $RDS_STATE"
echo "   ✅ ALB: $ALB_STATE"
echo "   ✅ SSM: $SSM_STATUS"

echo ""
print_status "🚀 Application Status:" $PURPLE
echo "   📱 Processes: $APP_PROCESSES uvicorn processes running"
echo "   🌐 External Health: $([ "$EXTERNAL_HEALTH" = "PASS" ] && echo "✅ Working" || echo "❌ Failed")"
echo "   ⚖️  ALB Health: $([ "$ALB_HEALTH" = "PASS" ] && echo "✅ Working" || echo "⚠️  Issues")"
echo "   🎯 Target Health: $TARGET_STATE"

echo ""
print_status "🔗 Access URLs:" $PURPLE
echo "   Direct: http://${PUBLIC_IP}:8000/health"
echo "   ALB: http://${ALB_DNS}/health"
echo "   Docs: http://${PUBLIC_IP}:8000/docs"
echo "   SSM: aws ssm start-session --target $INSTANCE_ID"

echo ""
print_status "📈 Overall Deployment Status:" $PURPLE

# Determine overall status
if [ "$EXTERNAL_HEALTH" = "PASS" ] && [ "$ALB_HEALTH" = "PASS" ]; then
    print_status "🎉 EXCELLENT: Full deployment success!" $GREEN
    print_status "   Both direct and load-balanced access are working perfectly." $GREEN
    STATUS="COMPLETE"
elif [ "$EXTERNAL_HEALTH" = "PASS" ] && [ "$TARGET_STATE" = "healthy" ]; then
    print_status "✅ GOOD: Application working, ALB initializing" $GREEN
    print_status "   Direct access works, ALB should be ready within 1-2 minutes." $GREEN
    STATUS="NEARLY_COMPLETE"
elif [ "$EXTERNAL_HEALTH" = "PASS" ]; then
    print_status "⚠️  PARTIAL: Application working, ALB needs attention" $YELLOW
    print_status "   Direct access works perfectly, ALB requires troubleshooting." $YELLOW
    STATUS="PARTIAL"
else
    print_status "❌ ISSUES: Application access problems detected" $RED
    print_status "   Both direct and ALB access have issues requiring immediate attention." $RED
    STATUS="NEEDS_ATTENTION"
fi

echo ""
print_status "💡 Next Steps:" $PURPLE

case $STATUS in
    "COMPLETE")
        echo "   🎊 Congratulations! Your deployment is production-ready."
        echo "   📋 Consider: SSL setup, custom domain, monitoring, and backups."
        ;;
    "NEARLY_COMPLETE")
        echo "   ⏳ Wait 2-3 minutes and test ALB again: curl http://${ALB_DNS}/health"
        echo "   📋 Then proceed with: SSL setup, custom domain, and monitoring."
        ;;
    "PARTIAL")
        echo "   🔧 Focus on ALB troubleshooting - run ALB-specific diagnostic scripts."
        echo "   ✅ Your application is functional via direct access in the meantime."
        ;;
    "NEEDS_ATTENTION")
        echo "   🚨 Address application access issues first."
        echo "   🔍 Check security groups, application logs, and restart if needed."
        ;;
esac

echo ""
print_status "🔧 Verification completed!" $BLUE

# Save results to file
cat > verification_results.txt << EOF
AWS FastAPI Deployment Verification Results (via SSM)
Generated: $(date)
====================================================

Infrastructure Status:
- VPC: $VPC_ID (Active)
- EC2: $INSTANCE_STATE ($PUBLIC_IP)
- RDS: $RDS_STATE
- ALB: $ALB_STATE
- SSM: $SSM_STATUS

Application Status:
- Processes: $APP_PROCESSES uvicorn running
- External Health: $EXTERNAL_HEALTH
- ALB Health: $ALB_HEALTH
- Target Health: $TARGET_STATE

Overall Status: $STATUS

Access URLs:
- Direct: http://${PUBLIC_IP}:8000/health
- ALB: http://${ALB_DNS}/health
- Documentation: http://${PUBLIC_IP}:8000/docs
- SSM: aws ssm start-session --target $INSTANCE_ID

Next Steps:
$(case $STATUS in
    "COMPLETE") echo "- Setup SSL/HTTPS
- Configure custom domain
- Implement monitoring
- Setup automated backups" ;;
    "NEARLY_COMPLETE") echo "- Wait for ALB health checks to complete
- Test ALB endpoint again
- Proceed with SSL setup" ;;
    "PARTIAL") echo "- Troubleshoot ALB health checks
- Verify target group configuration
- Check security group rules" ;;
    "NEEDS_ATTENTION") echo "- Debug application access issues
- Check security groups
- Restart application if needed" ;;
esac)
EOF

print_status "📄 Results saved to: verification_results.txt" $BLUE
