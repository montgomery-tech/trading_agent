#!/bin/bash

echo "🔧 Fixing Email Service Parameter Mismatch"
echo "=========================================="

echo "📋 The issue: admin.py calls send_welcome_email() with 'user_email=' but"
echo "   email_service.py expects 'email=' parameter"

echo ""
echo "🔧 Fixing api/services/email_service.py..."

# Fix the email service to match what admin.py is calling
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
    
    async def send_welcome_email(
        self, 
        user_email: str,  # ← Fixed: use user_email parameter name
        user_name: str, 
        username: str, 
        temporary_password: str, 
        login_url: str, 
        created_by_admin: str
    ) -> bool:
        """Send welcome email to new user (development: print to console)"""
        
        email_content = f"""
🎉 Welcome to the Trading System!

Hello {user_name},

Your account has been created successfully by {created_by_admin}!

📧 Email: {user_email}
👤 Username: {username}  
🔐 Temporary Password: {temporary_password}

⚠️  IMPORTANT: You must change your password on first login for security.

To get started:
1. Go to {login_url}
2. Use your username and temporary password  
3. You'll be prompted to create a new secure password
4. Then you can access all system features

If you have any questions, please contact your administrator.

Best regards,
Trading System Team
        """
        
        logger.info("📧 Welcome Email (Development Mode)")
        logger.info("=" * 50)
        logger.info(f"To: {user_email}")
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

echo "✅ Fixed api/services/email_service.py parameter names"

echo ""
echo "🧪 Testing the fix..."

# Test user creation with a new email
test_email="testuser$(date +%s)@example.com"

echo "   Creating user with email: $test_email"

response=$(curl -s -X POST http://localhost:8000/api/v1/admin/users \
  -H 'Content-Type: application/json' \
  -d "{\"email\":\"$test_email\",\"full_name\":\"Test User\",\"role\":\"trader\"}")

echo "   Response: $response"

if echo "$response" | grep -q "success.*true"; then
    echo "✅ User creation successful!"
    echo ""
    echo "🎉 Email service parameter issue FIXED!"
    echo ""
    echo "🚀 Now you can run your forced password change tests:"
    echo "   python3 test_forced_password_change_improved.py"
else
    echo "❌ Still having issues. Response:"
    echo "$response" | python3 -m json.tool 2>/dev/null || echo "$response"
fi
