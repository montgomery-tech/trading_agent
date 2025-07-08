#!/usr/bin/env python3
"""
Environment Validation Script
Validates environment configuration and security settings
"""

import os
import sys
import re
from pathlib import Path
from typing import List, Tuple, Dict, Any
import secrets
import hashlib


class EnvironmentValidator:
    """Validates environment configuration for security and completeness"""
    
    def __init__(self, env_file: str = ".env"):
        self.env_file = env_file
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.info: List[str] = []
        self.env_vars: Dict[str, str] = {}
        
    def load_env_file(self) -> bool:
        """Load and parse environment file"""
        if not Path(self.env_file).exists():
            self.errors.append(f"Environment file '{self.env_file}' not found")
            return False
        
        try:
            with open(self.env_file, 'r') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        self.env_vars[key.strip()] = value.strip()
            
            self.info.append(f"Loaded {len(self.env_vars)} environment variables from {self.env_file}")
            return True
        except Exception as e:
            self.errors.append(f"Failed to read {self.env_file}: {e}")
            return False
    
    def validate_secret_key(self) -> None:
        """Validate SECRET_KEY security"""
        secret_key = self.env_vars.get('SECRET_KEY', '')
        
        if not secret_key:
            self.errors.append("SECRET_KEY is missing")
            return
        
        # Check for default/weak keys
        weak_keys = [
            "your-secret-key-change-in-production",
            "secret",
            "password",
            "123456",
            "test",
            "development",
            "secret_key"
        ]
        
        if secret_key.lower() in [k.lower() for k in weak_keys]:
            self.errors.append("SECRET_KEY is using a weak/default value")
        
        # Check length
        if len(secret_key) < 32:
            self.errors.append(f"SECRET_KEY is too short ({len(secret_key)} chars), minimum 32 required")
        elif len(secret_key) < 64:
            self.warnings.append(f"SECRET_KEY could be longer ({len(secret_key)} chars), 64+ recommended")
        
        # Check entropy (basic)
        if len(set(secret_key)) < 16:
            self.warnings.append("SECRET_KEY has low character diversity")
        
        # Check if it's all alphanumeric (lower entropy)
        if secret_key.isalnum():
            self.warnings.append("SECRET_KEY should include special characters for higher entropy")
        
        self.info.append(f"SECRET_KEY length: {len(secret_key)} characters")
    
    def validate_database_config(self) -> None:
        """Validate database configuration"""
        database_url = self.env_vars.get('DATABASE_URL', '')
        environment = self.env_vars.get('ENVIRONMENT', 'development')
        
        if not database_url:
            self.errors.append("DATABASE_URL is missing")
            return
        
        # Check database type and environment compatibility
        if environment == 'production':
            if 'sqlite' in database_url.lower():
                self.warnings.append("SQLite not recommended for production, consider PostgreSQL")
            
            if 'localhost' in database_url and 'sqlite' not in database_url:
                self.warnings.append("Using localhost database in production")
            
            if database_url.startswith('postgresql://') and 'sslmode=require' not in database_url:
                self.warnings.append("SSL not enforced for PostgreSQL connection")
        
        # Check for credentials in URL
        if '@' in database_url:
            # Extract credentials part
            if '://' in database_url:
                creds_part = database_url.split('://')[1].split('@')[0]
                if ':' in creds_part:
                    username, password = creds_part.split(':', 1)
                    
                    # Validate password strength for non-development
                    if environment != 'development' and len(password) < 12:
                        self.warnings.append("Database password is shorter than 12 characters")
                    
                    if password.lower() in ['password', '123456', 'admin', username.lower()]:
                        self.errors.append("Database password is weak or predictable")
        
        self.info.append(f"Database type: {self._get_db_type(database_url)}")
    
    def validate_jwt_config(self) -> None:
        """Validate JWT configuration"""
        jwt_expire = self.env_vars.get('JWT_EXPIRE_MINUTES', '30')
        jwt_algorithm = self.env_vars.get('JWT_ALGORITHM', 'HS256')
        environment = self.env_vars.get('ENVIRONMENT', 'development')
        
        try:
            expire_minutes = int(jwt_expire)
            
            if expire_minutes <= 0:
                self.errors.append("JWT_EXPIRE_MINUTES must be positive")
            elif expire_minutes > 60 and environment == 'production':
                self.warnings.append("JWT tokens expire in >60 minutes, consider shorter duration for production")
            elif expire_minutes < 5:
                self.warnings.append("JWT tokens expire in <5 minutes, may cause usability issues")
            
        except ValueError:
            self.errors.append("JWT_EXPIRE_MINUTES must be a valid integer")
        
        if jwt_algorithm not in ['HS256', 'HS384', 'HS512', 'RS256', 'RS384', 'RS512']:
            self.warnings.append(f"JWT algorithm '{jwt_algorithm}' is not commonly recommended")
        
        self.info.append(f"JWT expires in {jwt_expire} minutes using {jwt_algorithm}")
    
    def validate_cors_config(self) -> None:
        """Validate CORS configuration"""
        cors_origins = self.env_vars.get('CORS_ORIGINS', '')
        environment = self.env_vars.get('ENVIRONMENT', 'development')
        
        if not cors_origins and environment != 'development':
            self.warnings.append("CORS_ORIGINS not configured for non-development environment")
            return
        
        origins = [origin.strip() for origin in cors_origins.split(',') if origin.strip()]
        
        for origin in origins:
            if origin == '*':
                if environment == 'production':
                    self.errors.append("CORS_ORIGINS should not contain '*' in production")
                else:
                    self.warnings.append("CORS_ORIGINS contains '*', not recommended for production")
            
            elif origin.startswith('http://') and environment == 'production':
                self.warnings.append(f"CORS origin '{origin}' uses HTTP, HTTPS recommended for production")
        
        self.info.append(f"CORS configured for {len(origins)} origins")
    
    def validate_rate_limiting(self) -> None:
        """Validate rate limiting configuration"""
        rate_limit_enabled = self.env_vars.get('RATE_LIMIT_ENABLED', 'true').lower()
        environment = self.env_vars.get('ENVIRONMENT', 'development')
        
        if rate_limit_enabled == 'false' and environment == 'production':
            self.warnings.append("Rate limiting disabled in production environment")
        
        if rate_limit_enabled == 'true':
            try:
                requests_per_minute = int(self.env_vars.get('RATE_LIMIT_REQUESTS_PER_MINUTE', '60'))
                if requests_per_minute <= 0:
                    self.errors.append("RATE_LIMIT_REQUESTS_PER_MINUTE must be positive")
                elif requests_per_minute > 1000:
                    self.warnings.append("Rate limit is very high, may not protect against abuse")
                
                self.info.append(f"Rate limiting: {requests_per_minute} requests/minute")
            except ValueError:
                self.errors.append("RATE_LIMIT_REQUESTS_PER_MINUTE must be a valid integer")
    
    def validate_email_config(self) -> None:
        """Validate email configuration"""
        email_enabled = self.env_vars.get('EMAIL_ENABLED', 'true').lower()
        
        if email_enabled == 'true':
            aws_key = self.env_vars.get('AWS_ACCESS_KEY_ID', '')
            aws_secret = self.env_vars.get('AWS_SECRET_ACCESS_KEY', '')
            
            if not aws_key:
                self.errors.append("AWS_ACCESS_KEY_ID required when EMAIL_ENABLED=true")
            elif len(aws_key) < 16:
                self.warnings.append("AWS_ACCESS_KEY_ID seems too short")
            
            if not aws_secret:
                self.errors.append("AWS_SECRET_ACCESS_KEY required when EMAIL_ENABLED=true")
            elif len(aws_secret) < 32:
                self.warnings.append("AWS_SECRET_ACCESS_KEY seems too short")
            
            from_email = self.env_vars.get('SES_FROM_EMAIL', '')
            if from_email and not self._is_valid_email(from_email):
                self.warnings.append(f"SES_FROM_EMAIL '{from_email}' doesn't look like a valid email")
        
        self.info.append(f"Email notifications: {'enabled' if email_enabled == 'true' else 'disabled'}")
    
    def validate_security_headers(self) -> None:
        """Validate security headers configuration"""
        environment = self.env_vars.get('ENVIRONMENT', 'development')
        https_only = self.env_vars.get('HTTPS_ONLY', 'false').lower()
        
        if environment == 'production' and https_only != 'true':
            self.warnings.append("HTTPS_ONLY should be enabled in production")
        
        security_headers = self.env_vars.get('SECURITY_HEADERS_ENABLED', 'true').lower()
        if security_headers != 'true' and environment == 'production':
            self.warnings.append("Security headers should be enabled in production")
    
    def validate_file_permissions(self) -> None:
        """Validate file permissions"""
        if not Path(self.env_file).exists():
            return
        
        try:
            stat_info = Path(self.env_file).stat()
            permissions = oct(stat_info.st_mode)[-3:]
            
            # Check if file is readable by others
            if permissions[2] != '0':
                self.warnings.append(f"Environment file has overly permissive permissions ({permissions}), consider 'chmod 600 {self.env_file}'")
            
            self.info.append(f"File permissions: {permissions}")
        except Exception as e:
            self.warnings.append(f"Could not check file permissions: {e}")
    
    def check_required_variables(self) -> None:
        """Check for required environment variables"""
        environment = self.env_vars.get('ENVIRONMENT', 'development')
        
        required_vars = ['SECRET_KEY', 'DATABASE_URL']
        
        if environment == 'production':
            required_vars.extend(['CORS_ORIGINS'])
        
        email_enabled = self.env_vars.get('EMAIL_ENABLED', 'true').lower()
        if email_enabled == 'true':
            required_vars.extend(['AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'SES_FROM_EMAIL'])
        
        for var in required_vars:
            if var not in self.env_vars or not self.env_vars[var]:
                self.errors.append(f"Required environment variable '{var}' is missing or empty")
    
    def generate_recommendations(self) -> List[str]:
        """Generate security recommendations"""
        recommendations = []
        environment = self.env_vars.get('ENVIRONMENT', 'development')
        
        if environment == 'production':
            recommendations.extend([
                "Use a managed database service (AWS RDS, Google Cloud SQL)",
                "Enable database connection encryption (SSL/TLS)",
                "Use AWS Secrets Manager or similar for credential management",
                "Implement log monitoring and alerting",
                "Set up automated backups",
                "Use a reverse proxy (nginx) with rate limiting",
                "Implement proper CI/CD with security scanning"
            ])
        
        if not self.env_vars.get('RATE_LIMIT_ENABLED', 'true').lower() == 'true':
            recommendations.append("Enable rate limiting to prevent abuse")
        
        if self.env_vars.get('DEBUG', 'false').lower() == 'true' and environment != 'development':
            recommendations.append("Disable DEBUG mode in non-development environments")
        
        return recommendations
    
    def _get_db_type(self, database_url: str) -> str:
        """Extract database type from URL"""
        if database_url.startswith('postgresql://') or database_url.startswith('postgres://'):
            return 'PostgreSQL'
        elif database_url.startswith('mysql://'):
            return 'MySQL'
        elif database_url.startswith('sqlite://'):
            return 'SQLite'
        else:
            return 'Unknown'
    
    def _is_valid_email(self, email: str) -> bool:
        """Basic email validation"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}
        return re.match(pattern, email) is not None
    
    def run_validation(self) -> bool:
        """Run complete validation suite"""
        print(f"🔍 Environment Validation Report for: {self.env_file}")
        print("=" * 60)
        
        if not self.load_env_file():
            self._print_results()
            return False
        
        # Run all validations
        self.check_required_variables()
        self.validate_secret_key()
        self.validate_database_config()
        self.validate_jwt_config()
        self.validate_cors_config()
        self.validate_rate_limiting()
        self.validate_email_config()
        self.validate_security_headers()
        self.validate_file_permissions()
        
        # Print results
        self._print_results()
        
        # Print recommendations
        recommendations = self.generate_recommendations()
        if recommendations:
            print("\n💡 Security Recommendations:")
            for i, rec in enumerate(recommendations, 1):
                print(f"   {i}. {rec}")
        
        return len(self.errors) == 0
    
    def _print_results(self) -> None:
        """Print validation results"""
        # Print errors
        if self.errors:
            print("\n❌ Errors (must be fixed):")
            for error in self.errors:
                print(f"   • {error}")
        
        # Print warnings
        if self.warnings:
            print("\n⚠️  Warnings (should be addressed):")
            for warning in self.warnings:
                print(f"   • {warning}")
        
        # Print info
        if self.info:
            print("\n✅ Configuration Info:")
            for info in self.info:
                print(f"   • {info}")
        
        # Summary
        print(f"\n📊 Summary:")
        print(f"   • Errors: {len(self.errors)}")
        print(f"   • Warnings: {len(self.warnings)}")
        print(f"   • Status: {'❌ FAILED' if self.errors else '✅ PASSED'}")


def main():
    """Main validation function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Validate environment configuration")
    parser.add_argument("--env-file", default=".env", help="Environment file to validate")
    parser.add_argument("--fail-on-warnings", action="store_true", help="Fail validation if warnings found")
    
    args = parser.parse_args()
    
    validator = EnvironmentValidator(args.env_file)
    success = validator.run_validation()
    
    # Exit with error code if validation failed
    if not success:
        sys.exit(1)
    
    if args.fail_on_warnings and validator.warnings:
        print("\n❌ Validation failed due to warnings (--fail-on-warnings enabled)")
        sys.exit(1)
    
    print(f"\n🎉 Environment validation successful!")


if __name__ == "__main__":
    main()
