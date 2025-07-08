#!/bin/bash

# =============================================================================
# Environment Setup Script for Trading System
# Sets up secure environment configuration for all deployment stages
# =============================================================================

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"

# =============================================================================
# Main Setup Function
# =============================================================================

setup_environment() {
    local env_type="${1:-development}"
    
    log_info "Setting up $env_type environment configuration..."
    
    # Create necessary directories
    mkdir -p logs
    mkdir -p config
    
    # Create .env file based on environment type
    case $env_type in
        "development")
            create_development_env
            ;;
        "staging")
            create_staging_env
            ;;
        "production")
            create_production_env
            ;;
        "testing")
            create_testing_env
            ;;
        *)
            log_error "Unknown environment type: $env_type"
            log_info "Valid options: development, staging, production, testing"
            exit 1
            ;;
    esac
    
    # Set secure file permissions
    chmod 600 .env
    log_success "Set secure file permissions (600) for .env"
    
    # Validate the environment
    if command -v python3 &> /dev/null; then
        log_info "Validating environment configuration..."
        python3 validate_environment.py --env-file .env
        if [ $? -eq 0 ]; then
            log_success "Environment validation passed!"
        else
            log_warning "Environment validation found issues. Please review and fix them."
        fi
    else
        log_warning "Python3 not found. Skipping environment validation."
    fi
    
    # Create .gitignore entry if needed
    if [ ! -f .gitignore ] || ! grep -q "^\.env$" .gitignore; then
        echo ".env" >> .gitignore
        log_success "Added .env to .gitignore"
    fi
    
    log_success "$env_type environment setup complete!"
    log_info "Environment file created: .env"
    log_info "Please review and update the configuration values as needed."
}

# =============================================================================
# Environment Creation Functions
# =============================================================================

create_development_env() {
    cat > .env << 'EOF'
# =============================================================================
# Development Environment Configuration
# =============================================================================

# Environment
ENVIRONMENT=development
DEBUG=true

# Security - Development Keys (CHANGE FOR OTHER ENVIRONMENTS)
SECRET_KEY=f19fb15492b88dbb703a5affeb215d308debaa49f91e47ce040e5ef8ad9be162
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=30
JWT_REFRESH_EXPIRE_DAYS=7

# Password Requirements
PASSWORD_MIN_LENGTH=8
PASSWORD_REQUIRE_UPPERCASE=true
PASSWORD_REQUIRE_LOWERCASE=true
PASSWORD_REQUIRE_NUMBERS=true
PASSWORD_REQUIRE_SPECIAL=false

# Database Configuration (Development - SQLite)
DATABASE_URL=sqlite:///balance_tracker.db

# API Configuration
API_V1_PREFIX=/api/v1
PROJECT_NAME=Balance Tracking System - Development
VERSION=1.0.0-dev

# CORS (Permissive for development)
CORS_ORIGINS=http://localhost:3000,http://localhost:8080,http://127.0.0.1:3000
CORS_ALLOW_CREDENTIALS=true

# Rate Limiting (Relaxed for development)
RATE_LIMIT_ENABLED=false
RATE_LIMIT_REQUESTS_PER_MINUTE=1000
RATE_LIMIT_BURST=50

# Email Configuration (Development - Disabled)
EMAIL_ENABLED=false
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_REGION=us-east-1
SES_FROM_EMAIL=dev@localhost
SES_FROM_NAME=Trading System Dev

# Security Headers (Relaxed for development)
SECURITY_HEADERS_ENABLED=true
HTTPS_ONLY=false

# Logging
LOG_LEVEL=DEBUG
LOG_FORMAT=detailed
LOG_FILE_ENABLED=false

# Monitoring
HEALTH_CHECK_ENABLED=true
METRICS_ENABLED=true
EOF
    
    log_success "Created development environment configuration"
    log_info "Default database: SQLite (balance_tracker.db)"
    log_info "Email: Disabled for development"
    log_info "Rate limiting: Disabled for development"
}

create_staging_env() {
    cat > .env << 'EOF'
# =============================================================================
# Staging Environment Configuration
# =============================================================================

# Environment
ENVIRONMENT=staging
DEBUG=false

# Security - Staging Keys (SECURE)
SECRET_KEY=f51d66c5d91440ca0a2e8112aae366a8a2f539bd54830bf535575d1744aaa55a
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=30
JWT_REFRESH_EXPIRE_DAYS=7

# Password Requirements (Stricter)
PASSWORD_MIN_LENGTH=8
PASSWORD_REQUIRE_UPPERCASE=true
PASSWORD_REQUIRE_LOWERCASE=true
PASSWORD_REQUIRE_NUMBERS=true
PASSWORD_REQUIRE_SPECIAL=true

# Database Configuration (Staging - PostgreSQL recommended)
DATABASE_URL=postgresql://staging_user:CHANGE_DATABASE_PASSWORD@localhost:5432/balance_tracker_staging
DATABASE_SSL_MODE=prefer
DATABASE_POOL_SIZE=10

# API Configuration
API_V1_PREFIX=/api/v1
PROJECT_NAME=Balance Tracking System - Staging
VERSION=1.0.0-staging

# CORS (Restricted for staging)
CORS_ORIGINS=https://staging.yourdomain.com
CORS_ALLOW_CREDENTIALS=true

# Rate Limiting (Production-like)
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS_PER_MINUTE=60
RATE_LIMIT_BURST=10

# Email Configuration (Staging - Update with real credentials)
EMAIL_ENABLED=true
AWS_ACCESS_KEY_ID=YOUR_STAGING_ACCESS_KEY
AWS_SECRET_ACCESS_KEY=YOUR_STAGING_SECRET_KEY
AWS_REGION=us-east-1
SES_FROM_EMAIL=staging@yourdomain.com
SES_FROM_NAME=Trading System Staging

# Security Headers
SECURITY_HEADERS_ENABLED=true
HTTPS_ONLY=true

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
LOG_FILE_ENABLED=true
LOG_FILE_PATH=logs/staging.log

# Monitoring
HEALTH_CHECK_ENABLED=true
METRICS_ENABLED=true
EOF
    
    log_success "Created staging environment configuration"
    log_warning "REQUIRED: Update DATABASE_URL with real credentials"
    log_warning "REQUIRED: Update AWS credentials for email functionality"
    log_warning "REQUIRED: Update CORS_ORIGINS with your staging domain"
}

create_production_env() {
    cat > .env << 'EOF'
# =============================================================================
# Production Environment Configuration
# =============================================================================

# Environment
ENVIRONMENT=production
DEBUG=false

# Security - Production Keys (MUST BE CHANGED)
SECRET_KEY=405348abf763b3f606f21160dfc3096c5ac8388473e5a749d46d31b4acd68f26
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=15
JWT_REFRESH_EXPIRE_DAYS=7

# Password Requirements (Strict)
PASSWORD_MIN_LENGTH=12
PASSWORD_REQUIRE_UPPERCASE=true
PASSWORD_REQUIRE_LOWERCASE=true
PASSWORD_REQUIRE_NUMBERS=true
PASSWORD_REQUIRE_SPECIAL=true

# Database Configuration (Production - AWS RDS PostgreSQL)
DATABASE_URL=postgresql://prod_user:CHANGE_DATABASE_PASSWORD@your-rds-endpoint.region.rds.amazonaws.com:5432/balance_tracker_prod
DATABASE_SSL_MODE=require
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=30

# API Configuration
API_V1_PREFIX=/api/v1
PROJECT_NAME=Balance Tracking System
VERSION=1.0.0

# CORS (Strict for production)
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
CORS_ALLOW_CREDENTIALS=true

# Rate Limiting (Strict)
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS_PER_MINUTE=60
RATE_LIMIT_BURST=5

# Email Configuration (Production - Amazon SES)
EMAIL_ENABLED=true
AWS_ACCESS_KEY_ID=YOUR_PRODUCTION_ACCESS_KEY
AWS_SECRET_ACCESS_KEY=YOUR_PRODUCTION_SECRET_KEY
AWS_REGION=us-east-1
SES_FROM_EMAIL=noreply@yourdomain.com
SES_FROM_NAME=Trading System

# Security Headers (Maximum security)
SECURITY_HEADERS_ENABLED=true
HTTPS_ONLY=true

# Logging (Production)
LOG_LEVEL=INFO
LOG_FORMAT=json
LOG_FILE_ENABLED=true
LOG_FILE_PATH=/var/log/trading-system/app.log

# Monitoring
HEALTH_CHECK_ENABLED=true
METRICS_ENABLED=true
EOF
    
    log_success "Created production environment configuration"
    log_error "CRITICAL: Update DATABASE_URL with real AWS RDS credentials"
    log_error "CRITICAL: Update AWS credentials for SES email service"
    log_error "CRITICAL: Update CORS_ORIGINS with your production domain(s)"
    log_warning "Review all security settings before deployment"
}

create_testing_env() {
    cat > .env << 'EOF'
# =============================================================================
# Testing Environment Configuration
# =============================================================================

# Environment
ENVIRONMENT=testing
DEBUG=true

# Security (Testing keys)
SECRET_KEY=test_secret_key_32_characters_long_for_testing_only
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=30

# Database Configuration (Testing - In-memory)
DATABASE_URL=sqlite:///:memory:

# Email (Disabled for testing)
EMAIL_ENABLED=false

# Rate Limiting (Disabled for testing)
RATE_LIMIT_ENABLED=false

# Logging (Minimal for testing)
LOG_LEVEL=WARNING
LOG_FORMAT=simple
LOG_FILE_ENABLED=false
EOF
    
    log_success "Created testing environment configuration"
    log_info "Using in-memory SQLite database for tests"
}

# =============================================================================
# Utility Functions
# =============================================================================

backup_existing_env() {
    if [ -f .env ]; then
        local backup_name=".env.backup.$(date +%Y%m%d_%H%M%S)"
        cp .env "$backup_name"
        log_info "Backed up existing .env to $backup_name"
    fi
}

generate_new_secrets() {
    log_info "Generating new cryptographically secure secrets..."
    
    # Generate SECRET_KEY
    local secret_key=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    log_success "New SECRET_KEY generated: ${secret_key:0:16}... (64 characters)"
    
    # Generate database password
    local db_password=$(python3 -c "import secrets, string; chars=string.ascii_letters+string.digits+'-_'; print(''.join(secrets.choice(chars) for _ in range(24)))")
    log_success "New database password generated: ${db_password:0:8}... (24 characters)"
    
    echo
    log_info "🔑 Copy these values to your .env file:"
    echo "SECRET_KEY=$secret_key"
    echo "DATABASE_PASSWORD=$db_password"
    echo
}

check_dependencies() {
    log_info "Checking dependencies..."
    
    # Check Python
    if command -v python3 &> /dev/null; then
        local python_version=$(python3 --version)
        log_success "Python found: $python_version"
    else
        log_warning "Python3 not found. Some features may not work."
    fi
    
    # Check if we're in the right directory
    if [ ! -f "main.py" ] && [ ! -f "api/config.py" ]; then
        log_warning "This doesn't appear to be the FastAPI project root directory"
        log_info "Make sure you're running this script from the fastapi_backend directory"
    fi
}

show_help() {
    cat << EOF
🔧 Environment Setup Script for Trading System

USAGE:
    $0 [COMMAND] [ENVIRONMENT_TYPE]

COMMANDS:
    setup [env_type]     Set up environment configuration (default: development)
    generate-secrets     Generate new cryptographic secrets
    validate            Validate existing .env file
    backup              Backup current .env file
    help                Show this help message

ENVIRONMENT TYPES:
    development         Development environment (SQLite, relaxed security)
    staging            Staging environment (PostgreSQL, production-like)
    production         Production environment (AWS RDS, strict security)
    testing            Testing environment (in-memory database)

EXAMPLES:
    $0 setup development      # Set up development environment
    $0 setup production       # Set up production environment
    $0 generate-secrets       # Generate new secrets
    $0 validate              # Validate current .env

SECURITY NOTES:
    • .env files are automatically added to .gitignore
    • File permissions are set to 600 (owner read/write only)
    • Production environments require manual credential updates
    • Never commit .env files to version control

EOF
}

# =============================================================================
# Main Script Logic
# =============================================================================

main() {
    local command="${1:-setup}"
    local env_type="${2:-development}"
    
    case $command in
        "setup")
            check_dependencies
            backup_existing_env
            setup_environment "$env_type"
            ;;
        "generate-secrets")
            generate_new_secrets
            ;;
        "validate")
            if [ -f .env ]; then
                if command -v python3 &> /dev/null; then
                    python3 validate_environment.py --env-file .env
                else
                    log_error "Python3 required for validation"
                    exit 1
                fi
            else
                log_error ".env file not found"
                exit 1
            fi
            ;;
        "backup")
            backup_existing_env
            ;;
        "help"|"-h"|"--help")
            show_help
            ;;
        *)
            log_error "Unknown command: $command"
            show_help
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"
