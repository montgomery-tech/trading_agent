#!/bin/bash

# ssl_https_setup.sh
# Phase 2: SSL/HTTPS Implementation for FastAPI on AWS
# Executor: SSL Certificate and HTTPS Configuration

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

print_status "🔒 SSL/HTTPS Setup for FastAPI on AWS" $BLUE
print_status "=====================================" $BLUE

# Load deployment information
source deployment_info.txt

echo ""
print_status "📋 Current Infrastructure:" $PURPLE
echo "   VPC: $VPC_ID"
echo "   EC2: $INSTANCE_ID ($PUBLIC_IP)"
echo "   ALB: $ALB_DNS"
echo "   Current HTTP URL: http://$ALB_DNS"

print_step "Phase 2 Options Analysis"

print_status "🔍 SSL Certificate Options:" $YELLOW

echo ""
echo "Option 1: AWS Certificate Manager (ACM) with Custom Domain"
echo "   ✅ Pros: Free SSL, auto-renewal, AWS managed"
echo "   ⚠️  Requires: Custom domain name"
echo "   📋 Steps: Domain → Route 53 → ACM → ALB HTTPS"
echo ""

echo "Option 2: Self-Signed Certificate for Testing"
echo "   ✅ Pros: Quick setup, no domain needed"
echo "   ⚠️  Cons: Browser warnings, not production-ready"
echo "   📋 Steps: Generate cert → Configure ALB"
echo ""

echo "Option 3: Let's Encrypt with Domain"
echo "   ✅ Pros: Free, trusted certificate"
echo "   ⚠️  Requires: Domain name and DNS control"
echo "   📋 Steps: Domain setup → Certbot → ALB config"
echo ""

print_status "💡 Recommendation for your case:" $BLUE
echo ""
echo "Since you mentioned using ALB DNS name until you have a custom domain:"
echo ""
echo "🚀 RECOMMENDED APPROACH:"
echo "   1. Set up ALB with self-signed cert for testing"
echo "   2. Configure HTTP→HTTPS redirect"
echo "   3. Test SSL functionality"
echo "   4. Later: Upgrade to ACM when you get custom domain"

print_step "Implementation Plan"

print_status "📋 Phase 2 Task Breakdown:" $PURPLE

echo ""
echo "Task 2.1: Generate Self-Signed SSL Certificate"
echo "   • Create SSL certificate for ALB DNS name"
echo "   • Upload certificate to AWS Certificate Manager"
echo "   • Success criteria: Certificate available in ACM"
echo ""

echo "Task 2.2: Configure ALB HTTPS Listener"
echo "   • Add HTTPS listener on port 443"
echo "   • Attach SSL certificate to listener"
echo "   • Success criteria: ALB accepts HTTPS connections"
echo ""

echo "Task 2.3: Set Up HTTP to HTTPS Redirect"
echo "   • Modify HTTP listener to redirect to HTTPS"
echo "   • Test redirect functionality"
echo "   • Success criteria: HTTP traffic automatically redirects"
echo ""

echo "Task 2.4: Update Security Groups"
echo "   • Allow inbound HTTPS (port 443) traffic"
echo "   • Verify security group rules"
echo "   • Success criteria: HTTPS traffic reaches ALB"
echo ""

echo "Task 2.5: Test and Verify SSL Implementation"
echo "   • Test HTTPS endpoints"
echo "   • Verify SSL certificate"
echo "   • Check redirect functionality"
echo "   • Success criteria: All endpoints work via HTTPS"

print_step "Quick Setup Execution"

print_status "🔧 Ready to implement SSL setup?" $YELLOW

echo ""
echo "This will configure:"
echo "   ✅ Self-signed SSL certificate"
echo "   ✅ HTTPS listener on ALB (port 443)"
echo "   ✅ HTTP→HTTPS redirect"
echo "   ✅ Security group updates"
echo ""

read -p "Continue with SSL setup? (y/n): " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    print_status "SSL setup cancelled. You can run this script later." $YELLOW
    exit 0
fi

print_step "Task 2.1: Creating Self-Signed SSL Certificate"

print_status "🔐 Generating SSL certificate for $ALB_DNS..." $YELLOW

# Create SSL certificate
openssl req -x509 -newkey rsa:4096 -keyout alb-private-key.pem -out alb-certificate.pem -days 365 -nodes -subj "/C=US/ST=State/L=City/O=Organization/CN=$ALB_DNS"

if [ $? -eq 0 ]; then
    print_status "✅ SSL certificate generated successfully" $GREEN
    echo "   Certificate: alb-certificate.pem"
    echo "   Private Key: alb-private-key.pem"
else
    print_status "❌ Failed to generate SSL certificate" $RED
    exit 1
fi

print_step "Task 2.2: Uploading Certificate to AWS"

print_status "📤 Uploading SSL certificate to AWS Certificate Manager..." $YELLOW

# Upload certificate to ACM
CERTIFICATE_ARN=$(aws acm import-certificate \
    --certificate fileb://alb-certificate.pem \
    --private-key fileb://alb-private-key.pem \
    --region us-east-1 \
    --query 'CertificateArn' \
    --output text)

if [ ! -z "$CERTIFICATE_ARN" ]; then
    print_status "✅ Certificate uploaded to ACM" $GREEN
    echo "   Certificate ARN: $CERTIFICATE_ARN"
    echo "CERTIFICATE_ARN=$CERTIFICATE_ARN" >> deployment_info.txt
else
    print_status "❌ Failed to upload certificate to ACM" $RED
    exit 1
fi

print_step "Task 2.3: Configuring ALB HTTPS Listener"

print_status "🔧 Adding HTTPS listener to ALB..." $YELLOW

# Create HTTPS listener
HTTPS_LISTENER_ARN=$(aws elbv2 create-listener \
    --load-balancer-arn $ALB_ARN \
    --protocol HTTPS \
    --port 443 \
    --certificates CertificateArn=$CERTIFICATE_ARN \
    --default-actions Type=forward,TargetGroupArn=$TARGET_GROUP_ARN \
    --region us-east-1 \
    --query 'Listeners[0].ListenerArn' \
    --output text)

if [ ! -z "$HTTPS_LISTENER_ARN" ]; then
    print_status "✅ HTTPS listener created successfully" $GREEN
    echo "   Listener ARN: $HTTPS_LISTENER_ARN"
    echo "HTTPS_LISTENER_ARN=$HTTPS_LISTENER_ARN" >> deployment_info.txt
else
    print_status "❌ Failed to create HTTPS listener" $RED
    exit 1
fi

print_step "Task 2.4: Setting Up HTTP to HTTPS Redirect"

print_status "🔄 Configuring HTTP to HTTPS redirect..." $YELLOW

# Get current HTTP listener ARN
HTTP_LISTENER_ARN=$(aws elbv2 describe-listeners \
    --load-balancer-arn $ALB_ARN \
    --query 'Listeners[?Port==`80`].ListenerArn' \
    --output text)

# Modify HTTP listener to redirect to HTTPS
aws elbv2 modify-listener \
    --listener-arn $HTTP_LISTENER_ARN \
    --default-actions Type=redirect,RedirectConfig='{Protocol=HTTPS,Port=443,StatusCode=HTTP_301}' \
    --region us-east-1

if [ $? -eq 0 ]; then
    print_status "✅ HTTP to HTTPS redirect configured" $GREEN
else
    print_status "❌ Failed to configure HTTP redirect" $RED
    exit 1
fi

print_step "Task 2.5: Updating Security Groups"

print_status "🔒 Adding HTTPS security group rules..." $YELLOW

# Add HTTPS inbound rule to ALB security group
aws ec2 authorize-security-group-ingress \
    --group-id $ALB_SG_ID \
    --protocol tcp \
    --port 443 \
    --cidr 0.0.0.0/0 \
    --region us-east-1

if [ $? -eq 0 ]; then
    print_status "✅ HTTPS security group rule added" $GREEN
else
    print_status "⚠️  HTTPS rule may already exist" $YELLOW
fi

print_step "Task 2.6: Testing SSL Implementation"

print_status "⏳ Waiting 30 seconds for SSL configuration to propagate..." $YELLOW
sleep 30

print_status "🧪 Testing HTTPS endpoints..." $YELLOW

# Test HTTPS health endpoint
echo ""
echo "Testing HTTPS health endpoint:"
if curl -k -f -s --connect-timeout 15 https://${ALB_DNS}/health > /dev/null 2>&1; then
    print_status "✅ HTTPS health endpoint working" $GREEN
    echo "Response:"
    curl -k -s https://${ALB_DNS}/health | python3 -m json.tool 2>/dev/null || curl -k -s https://${ALB_DNS}/health
else
    print_status "⚠️  HTTPS endpoint not ready yet" $YELLOW
    echo "This may take 2-3 more minutes to fully propagate"
fi

echo ""
echo "Testing HTTP to HTTPS redirect:"
HTTP_REDIRECT_TEST=$(curl -s -o /dev/null -w "%{http_code}" http://${ALB_DNS}/health)
if [ "$HTTP_REDIRECT_TEST" = "301" ]; then
    print_status "✅ HTTP to HTTPS redirect working" $GREEN
elif [ "$HTTP_REDIRECT_TEST" = "200" ]; then
    print_status "⚠️  HTTP still serving content (redirect may need more time)" $YELLOW
else
    print_status "⚠️  HTTP redirect status: $HTTP_REDIRECT_TEST" $YELLOW
fi

print_step "SSL Implementation Results"

echo ""
print_status "📊 SSL/HTTPS SETUP SUMMARY" $BLUE
print_status "===========================" $BLUE

echo ""
print_status "✅ Completed SSL Tasks:" $GREEN
echo "   • Self-signed SSL certificate generated"
echo "   • Certificate uploaded to AWS ACM"
echo "   • HTTPS listener added to ALB (port 443)"
echo "   • HTTP to HTTPS redirect configured"
echo "   • Security groups updated for HTTPS"

echo ""
print_status "🔗 New SSL URLs:" $BLUE
echo "   HTTPS: https://$ALB_DNS/health"
echo "   HTTPS Docs: https://$ALB_DNS/docs"
echo "   HTTP (redirects): http://$ALB_DNS (→ HTTPS)"

echo ""
print_status "🧪 Test Commands:" $PURPLE
echo "   curl -k https://$ALB_DNS/health"
echo "   curl -I http://$ALB_DNS (should show 301 redirect)"
echo "   curl -k https://$ALB_DNS/docs"

echo ""
print_status "⚠️  Important Notes:" $YELLOW
echo "   • Using -k flag to ignore self-signed certificate warnings"
echo "   • Browser will show security warning (expected for self-signed)"
echo "   • For production: Replace with ACM certificate + custom domain"
echo "   • SSL configuration may take 2-3 minutes to fully propagate"

echo ""
print_status "🎯 Next Steps:" $BLUE
echo "   • Test HTTPS endpoints work correctly"
echo "   • Verify HTTP→HTTPS redirect functions"
echo "   • When ready: Set up custom domain + ACM certificate"
echo "   • Consider implementing Phase 3 (Monitoring)"

# Clean up certificate files
rm -f alb-certificate.pem alb-private-key.pem

echo ""
print_status "🔒 Phase 2 SSL setup completed!" $GREEN

# Update deployment summary
cat >> deployment_summary.txt << EOF

SSL/HTTPS Configuration (Phase 2):
- SSL Certificate: Self-signed (uploaded to ACM)
- HTTPS Listener: Port 443 configured
- HTTP Redirect: Enabled (HTTP→HTTPS)
- Security Groups: Updated for HTTPS traffic
- HTTPS URL: https://$ALB_DNS
EOF

print_status "📄 Updated deployment_summary.txt with SSL information" $BLUE
