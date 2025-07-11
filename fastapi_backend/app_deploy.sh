#!/bin/bash
# FastAPI Application Deployment Script
# Deploys the trading API to EC2 instance

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

# Check if infrastructure is deployed
check_infrastructure() {
    if [ ! -f vpc_info.txt ]; then
        print_status "❌ Infrastructure not found. Run the infrastructure deployment first." $RED
        exit 1
    fi
    
    source vpc_info.txt
    print_status "✅ Found infrastructure deployment" $GREEN
}

# Create production environment file
create_production_env() {
    print_step "Creating Production Environment Configuration"
    
    source vpc_info.txt
    
    cat > .env.production << EOF
# =============================================================================
# Production Environment Configuration
# AWS Deployment
# =============================================================================

# Environment
ENVIRONMENT=production
DEBUG=false

# Security - Production Keys (CHANGE THESE!)
SECRET_KEY=CHANGE_THIS_TO_SECURE_RANDOM_STRING_IN_PRODUCTION
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=15
JWT_REFRESH_EXPIRE_DAYS=7

# Password Requirements
PASSWORD_MIN_LENGTH=8
PASSWORD_REQUIRE_UPPERCASE=true
PASSWORD_REQUIRE_LOWERCASE=true
PASSWORD_REQUIRE_NUMBERS=true
PASSWORD_REQUIRE_SPECIAL=true

# Database Configuration - AWS RDS PostgreSQL
DATABASE_URL=postgresql://dbadmin:${DB_PASSWORD}@${RDS_ENDPOINT}:5432/balance_tracker
DATABASE_TYPE=postgresql

# API Configuration
API_V1_PREFIX=/api/v1
PROJECT_NAME=Trading API - Production
VERSION=1.0.0

# CORS (Restrictive for production)
CORS_ORIGINS=https://yourdomain.com,https://api.yourdomain.com
CORS_ALLOW_CREDENTIALS=true

# Rate Limiting (Production - Strict)
RATE_LIMIT_ENABLED=true
RATE_LIMIT_AUTH_REQUESTS=5
RATE_LIMIT_TRADING_REQUESTS=50
RATE_LIMIT_INFO_REQUESTS=100
RATE_LIMIT_ADMIN_REQUESTS=3
RATE_LIMIT_REQUESTS_PER_MINUTE=30

# Advanced Rate Limiting Features
RATE_LIMIT_SLIDING_WINDOW=true
RATE_LIMIT_BURST_PROTECTION=true
RATE_LIMIT_ADMIN_BYPASS=false

# Email Configuration (Production - Configure if needed)
EMAIL_ENABLED=false
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_REGION=us-east-1
SES_FROM_EMAIL=noreply@yourdomain.com
SES_FROM_NAME=Trading API

# Security Headers (Strict for production)
SECURITY_HEADERS_ENABLED=true
HTTPS_ONLY=true
HSTS_MAX_AGE=31536000

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
LOG_FILE_ENABLED=true
LOG_FILE_PATH=/var/log/trading-api/app.log

# Monitoring
HEALTH_CHECK_ENABLED=true
METRICS_ENABLED=true

# Security Configuration
MAX_REQUEST_SIZE=1048576
REQUEST_TIMEOUT=30
EOF
    
    print_status "✅ Created production environment file" $GREEN
    print_status "⚠️  IMPORTANT: Update SECRET_KEY and CORS_ORIGINS in .env.production" $YELLOW
}

# Create PM2 ecosystem file
create_pm2_config() {
    print_step "Creating PM2 Configuration"
    
    cat > ecosystem.config.js << 'EOF'
module.exports = {
  apps: [{
    name: 'trading-api',
    script: '/usr/bin/python3',
    args: '-m uvicorn main:app --host 0.0.0.0 --port 8000',
    cwd: '/opt/trading-api',
    instances: 1,
    autorestart: true,
    watch: false,
    max_memory_restart: '500M',
    env: {
      NODE_ENV: 'production',
      PYTHONPATH: '/opt/trading-api'
    },
    env_production: {
      NODE_ENV: 'production'
    },
    log_file: '/var/log/trading-api/combined.log',
    out_file: '/var/log/trading-api/out.log',
    error_file: '/var/log/trading-api/error.log',
    time: true
  }]
};
EOF
    
    print_status "✅ Created PM2 configuration" $GREEN
}

# Create deployment package
create_deployment_package() {
    print_step "Creating Deployment Package"
    
    # Create a deployment directory
    mkdir -p deployment_package
    
    # Copy FastAPI application files
    if [ -d "api" ]; then
        cp -r api deployment_package/
        print_status "✅ Copied API modules" $GREEN
    else
        print_status "❌ API directory not found. Are you in the fastapi_backend directory?" $RED
        exit 1
    fi
    
    # Copy main application files
    for file in main.py requirements.txt; do
        if [ -f "$file" ]; then
            cp "$file" deployment_package/
            print_status "✅ Copied $file" $GREEN
        else
            print_status "⚠️  Warning: $file not found" $YELLOW
        fi
    done
    
    # Copy configuration files
    cp .env.production deployment_package/.env
    cp ecosystem.config.js deployment_package/
    
    # Create database schema file if it exists
    if [ -f "setup_database.py" ]; then
        cp setup_database.py deployment_package/
    fi
    
    # Create deployment scripts
    cat > deployment_package/deploy.sh << 'EOF'
#!/bin/bash
# Application deployment script (runs on EC2)

set -e

echo "🚀 Deploying Trading API..."

# Install Python dependencies
pip3 install -r requirements.txt

# Create log directory
sudo mkdir -p /var/log/trading-api
sudo chown ec2-user:ec2-user /var/log/trading-api

# Set up database (if schema file exists)
if [ -f "setup_database.py" ]; then
    echo "Setting up database schema..."
    python3 setup_database.py postgresql
fi

# Start application with PM2
pm2 start ecosystem.config.js --env production
pm2 save
pm2 startup

echo "✅ Deployment completed!"
echo "🌐 API should be available at the load balancer endpoint"
EOF
    
    chmod +x deployment_package/deploy.sh
    
    # Create a tarball
    tar -czf trading-api-deployment.tar.gz -C deployment_package .
    
    print_status "✅ Created deployment package: trading-api-deployment.tar.gz" $GREEN
}

# Deploy to EC2 instance
deploy_to_ec2() {
    print_step "Deploying Application to EC2"
    
    source vpc_info.txt
    
    # Wait for EC2 to be ready
    print_status "⏳ Waiting for EC2 instance to be ready..." $YELLOW
    sleep 30  # Give instance time to complete user data script
    
    # Copy deployment package to EC2
    print_status "📦 Uploading deployment package..." $YELLOW
    scp -i trading-api-keypair.pem -o StrictHostKeyChecking=no \
        trading-api-deployment.tar.gz \
        ec2-user@${PUBLIC_IP}:/tmp/
    
    # Connect to EC2 and deploy
    print_status "🚀 Deploying application..." $YELLOW
    ssh -i trading-api-keypair.pem -o StrictHostKeyChecking=no ec2-user@${PUBLIC_IP} << 'EOF'
# Extract deployment package
cd /opt/trading-api
sudo tar -xzf /tmp/trading-api-deployment.tar.gz
sudo chown -R ec2-user:ec2-user /opt/trading-api

# Run deployment script
chmod +x deploy.sh
./deploy.sh

# Check if application is running
sleep 5
curl -f http://localhost:8000/health || echo "⚠️ Application may not be ready yet"

echo "✅ Application deployment completed"
EOF
    
    print_status "✅ Application deployed to EC2" $GREEN
}

# Test deployment
test_deployment() {
    print_step "Testing Deployment"
    
    source vpc_info.txt
    
    # Test direct EC2 access
    print_status "🧪 Testing direct EC2 access..." $YELLOW
    if curl -f -s http://${PUBLIC_IP}:8000/health > /dev/null; then
        print_status "✅ EC2 direct access working" $GREEN
    else
        print_status "❌ EC2 direct access failed" $RED
    fi
    
    # Test load balancer access
    print_status "🧪 Testing load balancer access..." $YELLOW
    sleep 10  # Give ALB time to register target
    
    if curl -f -s http://${ALB_DNS}/health > /dev/null; then
        print_status "✅ Load balancer access working" $GREEN
    else
        print_status "⚠️ Load balancer access failed (may need more time)" $YELLOW
    fi
    
    # Show API endpoints
    print_status "🌐 API Endpoints:" $BLUE
    echo "  Health Check: http://${ALB_DNS}/health"
    echo "  API Documentation: http://${ALB_DNS}/docs"
    echo "  Authentication: http://${ALB_DNS}/api/v1/auth"
    echo "  Trading: http://${ALB_DNS}/api/v1/trades"
    echo "  Balances: http://${ALB_DNS}/api/v1/balances"
    echo "  Transactions: http://${ALB_DNS}/api/v1/transactions"
}

# Create SSL certificate (optional)
setup_ssl() {
    print_step "SSL Certificate Setup"
    
    print_status "To set up HTTPS, you need:" $YELLOW
    echo "1. A domain name pointed to your load balancer"
    echo "2. AWS Certificate Manager certificate"
    echo "3. HTTPS listener on the load balancer"
    echo ""
    echo "Steps:"
    echo "1. Register a domain (e.g., Route 53, GoDaddy)"
    echo "2. Create CNAME record: api.yourdomain.com -> ${ALB_DNS}"
    echo "3. Request SSL certificate in AWS Certificate Manager"
    echo "4. Add HTTPS listener to load balancer"
    echo ""
    print_status "📚 See AWS documentation for detailed SSL setup" $BLUE
}

# Create database migration script
create_db_migration() {
    print_step "Database Migration"
    
    source vpc_info.txt
    
    print_status "To migrate your local database to RDS:" $YELLOW
    echo ""
    echo "1. Export local database:"
    echo "   pg_dump -h localhost -U user balance_tracker > local_backup.sql"
    echo ""
    echo "2. Import to RDS:"
    echo "   psql -h ${RDS_ENDPOINT} -U dbadmin -d balance_tracker < local_backup.sql"
    echo ""
    echo "3. Or connect directly to RDS:"
    echo "   psql -h ${RDS_ENDPOINT} -U dbadmin -d balance_tracker"
    echo ""
    print_status "🔐 Database password: ${DB_PASSWORD}" $GREEN
}

# Generate final summary
generate_deployment_summary() {
    print_step "Deployment Summary"
    
    source vpc_info.txt
    
    cat > final_deployment_summary.txt << EOF
===========================================
Trading API Deployment Complete
===========================================

🌐 Your API is now live at:
   Load Balancer: http://${ALB_DNS}
   Health Check: http://${ALB_DNS}/health
   Documentation: http://${ALB_DNS}/docs

🔗 API Endpoints:
   Authentication: http://${ALB_DNS}/api/v1/auth
   Trading: http://${ALB_DNS}/api/v1/trades
   Balances: http://${ALB_DNS}/api/v1/balances
   Transactions: http://${ALB_DNS}/api/v1/transactions

🗄️ Database Access:
   Host: ${RDS_ENDPOINT}
   Port: 5432
   Database: balance_tracker
   Username: dbadmin
   Password: ${DB_PASSWORD}

🔧 Management:
   SSH to EC2: ssh -i trading-api-keypair.pem ec2-user@${PUBLIC_IP}
   PM2 Status: pm2 status
   PM2 Logs: pm2 logs trading-api
   PM2 Restart: pm2 restart trading-api

📊 Monitoring:
   Application Logs: /var/log/trading-api/
   EC2 Instance: ${INSTANCE_ID}
   Load Balancer: ${ALB_DNS}

💰 Estimated Monthly Cost: $0-40 (depending on Free Tier)

🔒 Security Notes:
   - Update SECRET_KEY in .env
   - Configure CORS_ORIGINS for your domain
   - Set up SSL certificate for HTTPS
   - Review security groups as needed

🚀 Next Steps:
   1. Set up custom domain and SSL
   2. Configure monitoring and alerts
   3. Set up automated backups
   4. Configure CI/CD pipeline
EOF
    
    cat final_deployment_summary.txt
    print_status "📄 Summary saved to: final_deployment_summary.txt" $BLUE
}

# Main deployment workflow
deploy_application() {
    print_status "🚀 Starting FastAPI Application Deployment" $BLUE
    
    check_infrastructure
    create_production_env
    create_pm2_config
    create_deployment_package
    deploy_to_ec2
    test_deployment
    create_db_migration
    setup_ssl
    generate_deployment_summary
    
    print_status "🎉 Application deployment completed successfully!" $GREEN
}

# Command line interface
case "${1:-deploy}" in
    "deploy")
        deploy_application
        ;;
    "test")
        source vpc_info.txt
        test_deployment
        ;;
    "logs")
        source vpc_info.txt
        ssh -i trading-api-keypair.pem ec2-user@${PUBLIC_IP} "pm2 logs trading-api"
        ;;
    "status")
        source vpc_info.txt
        ssh -i trading-api-keypair.pem ec2-user@${PUBLIC_IP} "pm2 status"
        ;;
    "restart")
        source vpc_info.txt
        ssh -i trading-api-keypair.pem ec2-user@${PUBLIC_IP} "pm2 restart trading-api"
        ;;
    *)
        echo "Usage: $0 [deploy|test|logs|status|restart]"
        echo "  deploy  - Deploy application (default)"
        echo "  test    - Test deployment"
        echo "  logs    - View application logs"
        echo "  status  - Check PM2 status"
        echo "  restart - Restart application"
        exit 1
        ;;
esac
