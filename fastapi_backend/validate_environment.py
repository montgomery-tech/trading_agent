#!/usr/bin/env python3
"""
Environment Validation Script - FIXED VERSION
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

        self.info.append(f"Database type: {self._get_db_type(database_url)}")

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

    def validate_email_config(self) -> None:
        """Validate email configuration"""
        email_enabled = self.env_vars.get('EMAIL_ENABLED', 'true').lower()

        if email_enabled == 'true':
            aws_key = self.env_vars.get('AWS_ACCESS_KEY_ID', '')
            aws_secret = self.env_vars.get('AWS_SECRET_ACCESS_KEY', '')

            if not aws_key:
                self.warnings.append("AWS_ACCESS_KEY_ID not set (email disabled)")
            if not aws_secret:
                self.warnings.append("AWS_SECRET_ACCESS_KEY not set (email disabled)")

            from_email = self.env_vars.get('SES_FROM_EMAIL', '')
            if from_email and not self._is_valid_email(from_email):
                self.warnings.append(f"SES_FROM_EMAIL '{from_email}' doesn't look like a valid email")

        self.info.append(f"Email notifications: {'enabled' if email_enabled == 'true' else 'disabled'}")

    def check_required_variables(self) -> None:
        """Check for required environment variables"""
        environment = self.env_vars.get('ENVIRONMENT', 'development')

        required_vars = ['SECRET_KEY', 'DATABASE_URL']

        for var in required_vars:
            if var not in self.env_vars or not self.env_vars[var]:
                self.errors.append(f"Required environment variable '{var}' is missing or empty")

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
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
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
        self.validate_cors_config()
        self.validate_email_config()

        # Print results
        self._print_results()

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

    args = parser.parse_args()

    validator = EnvironmentValidator(args.env_file)
    success = validator.run_validation()

    # Exit with error code if validation failed
    if not success:
        sys.exit(1)

    print(f"\n🎉 Environment validation successful!")


if __name__ == "__main__":
    main()
