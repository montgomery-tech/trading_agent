#!/bin/bash

# =============================================================================
# Missing Files Check and Creation Script
# Ensures all required files exist for the admin/auth system
# =============================================================================

echo "🔍 Checking for Missing Files"
echo "=============================="

# Function to create a file with content if it doesn't exist
create_file_if_missing() {
    local filepath="$1"
    local content="$2"
    
    if [[ ! -f "$filepath" ]]; then
        echo "📁 Creating missing file: $filepath"
        mkdir -p "$(dirname "$filepath")"
        echo "$content" > "$filepath"
        echo "✅ Created $filepath"
    else
        echo "✅ Found $filepath"
    fi
}

# Check and create __init__.py files
echo "📦 Checking Python package __init__.py files..."
create_file_if_missing "api/__init__.py" ""
create_file_if_missing "api/models/__init__.py" ""
create_file_if_missing "api/routes/__init__.py" ""
create_file_if_missing "api/services/__init__.py" ""

echo ""
echo "📋 Checking critical model files..."

# Check for user_admin.py models
if [[ ! -f "api/models/user_admin.py" ]]; then
    echo "📁 Creating api/models/user_admin.py..."
    cat > api/models/user_admin.py << 'EOF'
"""
User Admin Models for Admin User Creation System
"""

from pydantic import BaseModel, EmailStr, validator, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class UserRole(str, Enum):
    """User roles for access control"""
    ADMIN = "admin"
    TRADER = "trader" 
    USER = "user"
    VIEWER = "viewer"


class CreateUserRequest(BaseModel):
    """Request model for admin user creation"""
    email: EmailStr
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)
    role: UserRole = UserRole.USER
    
    @validator('first_name')
    def validate_first_name(cls, v):
        return v.strip()
    
    @validator('last_name')
    def validate_last_name(cls, v):
        return v.strip()


class CreateUserResponse(BaseModel):
    """Response model for successful user creation"""
    success: bool = True
    message: str
    user_id: str
    username: str
    email: str
    temporary_password: str
    must_change_password: bool = True


class UserListResponse(BaseModel):
    """Response model for user list"""
    id: str
    username: str
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role: UserRole
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime] = None
    must_change_password: bool = False
EOF
    echo "✅ Created api/models/user_admin.py"
else
    echo "✅ Found api/models/user_admin.py"
fi

# Check for email service
if [[ ! -f "api/services/email_service.py" ]]; then
    echo "📁 Creating api/services/email_service.py..."
    cat > api/services/email_service.py << 'EOF'
"""
Email Service for Admin User Creation
Development version - prints emails to console
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class EmailService:
    """Email service for development (console output)"""
    
    def __init__(self):
        self.enabled = False  # Disabled for development
        logger.info("📧 Email service initialized (development mode - console output)")
    
    async def send_welcome_email(self, email: str, username: str, temporary_password: str) -> bool:
        """Send welcome email to new user (development: print to console)"""
        
        email_content = f"""
🎉 Welcome to the Trading System!

Hello {username},

Your account has been created successfully!

📧 Email: {email}
👤 Username: {username}
🔐 Temporary Password: {temporary_password}

⚠️  IMPORTANT: You must change your password on first login for security.

To get started:
1. Go to the login page
2. Use your email and temporary password
3. You'll be prompted to create a new secure password
4. Then you can access all system features

If you have any questions, please contact your administrator.

Best regards,
Trading System Team
        """
        
        logger.info("📧 Welcome Email (Development Mode)")
        logger.info("=" * 50)
        logger.info(f"To: {email}")
        logger.info(f"Subject: Welcome to Trading System - Action Required")
        logger.info("Content:")
        logger.info(email_content)
        logger.info("=" * 50)
        
        return True
    
    async def send_password_reset_email(self, email: str, reset_token: str) -> bool:
        """Send password reset email"""
        
        logger.info(f"📧 Password Reset Email (Development): {email}")
        logger.info(f"Reset Token: {reset_token}")
        
        return True


# Global email service instance
email_service = EmailService()
EOF
    echo "✅ Created api/services/email_service.py"
else
    echo "✅ Found api/services/email_service.py"
fi

# Check for auth models
if [[ ! -f "api/models/auth.py" ]]; then
    echo "📁 Creating api/models/auth.py..."
    cat > api/models/auth.py << 'EOF'
"""
Authentication Models
"""

from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


class LoginRequest(BaseModel):
    """Login request model"""
    username: str  # Can be email or username
    password: str


class LoginResponse(BaseModel):
    """Login response model"""
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: int
    must_change_password: bool = False
    temporary_token: Optional[str] = None


class PasswordChangeRequest(BaseModel):
    """Password change request model"""
    current_password: str = ""  # Empty for temporary token usage
    new_password: str


class TokenRefreshRequest(BaseModel):
    """Token refresh request model"""
    refresh_token: str


class UserProfile(BaseModel):
    """User profile model"""
    id: str
    username: str
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_active: bool
    is_verified: bool = False
    created_at: datetime
    last_login: Optional[datetime] = None
    must_change_password: bool = False
EOF
    echo "✅ Created api/models/auth.py"
else
    echo "✅ Found api/models/auth.py"
fi

echo ""
echo "🔍 Checking main application files..."

# Check if main.py exists
if [[ ! -f "main.py" ]]; then
    echo "❌ main.py is missing! This is critical."
    echo "   Please ensure main.py exists before running the admin fix."
    exit 1
else
    echo "✅ Found main.py"
fi

# Check if database dependencies exist
if [[ ! -f "api/dependencies.py" ]] && [[ ! -f "api/database.py" ]]; then
    echo "⚠️  Database dependencies appear to be missing"
    echo "   This may cause import errors in admin routes"
fi

echo ""
echo "🎯 File Check Summary"
echo "===================="
echo "✅ All required files are now present"
echo ""
echo "🚀 Next Steps:"
echo "   1. Run the admin router fix:"
echo "      python3 fix_main_py_admin.py"
echo "   2. Restart your FastAPI server"
echo "   3. Test the admin endpoints"
echo ""
echo "📝 Note: Email service is configured for development"
echo "   Emails will be printed to console instead of sent"
