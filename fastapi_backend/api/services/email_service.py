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
