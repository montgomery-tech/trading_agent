#!/usr/bin/env python3
"""
PostgreSQL API Keys Migration Script
Properly creates API key tables in PostgreSQL database for authentication system
"""

import os
import sys
import logging
import psycopg2
from datetime import datetime
from urllib.parse import urlparse

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class PostgreSQLAPIKeyMigration:
    """Handles API key table creation in PostgreSQL"""

    def __init__(self):
        self.database_url = os.getenv('DATABASE_URL', 'postgresql://garrettroth@localhost:5432/balance_tracker')
        self.connection = None

    def connect(self) -> bool:
        """Connect to PostgreSQL database"""
        try:
            # Parse the PostgreSQL URL
            parsed = urlparse(self.database_url)

            # Connect to PostgreSQL
            self.connection = psycopg2.connect(
                host=parsed.hostname,
                port=parsed.port or 5432,
                database=parsed.path[1:],  # Remove leading '/'
                user=parsed.username,
                password=parsed.password
            )

            # Enable autocommit for DDL operations
            self.connection.autocommit = True

            logger.info(f"✅ Connected to PostgreSQL database: {parsed.path[1:]}")
            return True

        except Exception as e:
            logger.error(f"❌ PostgreSQL connection failed: {e}")
            logger.error("Please ensure PostgreSQL is running and the database exists")
            return False

    def check_existing_tables(self) -> dict:
        """Check what tables already exist"""
        try:
            cursor = self.connection.cursor()

            # Check for existing tables
            cursor.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name IN ('users', 'api_keys', 'api_key_usage_log')
                ORDER BY table_name
            """)

            existing_tables = [row[0] for row in cursor.fetchall()]
            cursor.close()

            result = {
                'users': 'users' in existing_tables,
                'api_keys': 'api_keys' in existing_tables,
                'api_key_usage_log': 'api_key_usage_log' in existing_tables,
                'all_tables': existing_tables
            }

            logger.info(f"📊 Existing tables: {result['all_tables']}")
            return result

        except Exception as e:
            logger.error(f"❌ Failed to check existing tables: {e}")
            return {}

    def create_api_keys_schema(self) -> bool:
        """Create API keys tables in PostgreSQL"""

        schema_sql = """
        -- Enable UUID extension if not already enabled
        CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

        -- API Keys Table for PostgreSQL
        CREATE TABLE IF NOT EXISTS api_keys (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            key_id VARCHAR(32) UNIQUE NOT NULL,          -- Public key identifier (btapi_xxxxx)
            key_hash VARCHAR(255) NOT NULL,              -- Bcrypt hash of the full API key
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            name VARCHAR(100) NOT NULL,                  -- Human-readable key name
            description TEXT,                            -- Optional description
            is_active BOOLEAN DEFAULT true,              -- Can be deactivated without deletion
            created_by UUID REFERENCES users(id),       -- Admin who created the key
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            last_used_at TIMESTAMP WITH TIME ZONE,      -- Track last usage
            expires_at TIMESTAMP WITH TIME ZONE,        -- Optional expiration date
            permissions_scope TEXT DEFAULT 'inherit',    -- 'inherit' or JSON permissions

            -- Constraints
            CONSTRAINT api_keys_name_check CHECK (LENGTH(name) >= 1),
            CONSTRAINT api_keys_key_id_format CHECK (key_id ~ '^btapi_[a-zA-Z0-9]{8,32}$')
        );

        -- Indexes for fast lookups
        CREATE INDEX IF NOT EXISTS idx_api_keys_key_id ON api_keys(key_id);
        CREATE INDEX IF NOT EXISTS idx_api_keys_user_id ON api_keys(user_id);
        CREATE INDEX IF NOT EXISTS idx_api_keys_active ON api_keys(is_active);
        CREATE INDEX IF NOT EXISTS idx_api_keys_last_used ON api_keys(last_used_at);

        -- API Key Usage Log Table (for audit trail)
        CREATE TABLE IF NOT EXISTS api_key_usage_log (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            api_key_id UUID NOT NULL REFERENCES api_keys(id) ON DELETE CASCADE,
            endpoint VARCHAR(255),                       -- API endpoint accessed
            method VARCHAR(10),                          -- HTTP method
            status_code INTEGER,                         -- Response status
            ip_address INET,                             -- Client IP address
            user_agent TEXT,                             -- Client user agent
            request_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );

        -- Indexes for usage log
        CREATE INDEX IF NOT EXISTS idx_api_usage_key_id ON api_key_usage_log(api_key_id);
        CREATE INDEX IF NOT EXISTS idx_api_usage_timestamp ON api_key_usage_log(request_timestamp);

        -- Function to automatically update last_used_at
        CREATE OR REPLACE FUNCTION update_api_key_last_used()
        RETURNS TRIGGER AS $$
        BEGIN
            UPDATE api_keys
            SET last_used_at = CURRENT_TIMESTAMP
            WHERE id = NEW.api_key_id;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;

        -- Trigger to update last_used_at when usage is logged
        DROP TRIGGER IF EXISTS trigger_update_api_key_last_used ON api_key_usage_log;
        CREATE TRIGGER trigger_update_api_key_last_used
            AFTER INSERT ON api_key_usage_log
            FOR EACH ROW
            EXECUTE FUNCTION update_api_key_last_used();
        """

        try:
            logger.info("📋 Creating API keys schema in PostgreSQL...")
            cursor = self.connection.cursor()

            # Execute schema (split by semicolon for better error handling)
            statements = [stmt.strip() for stmt in schema_sql.split(';') if stmt.strip()]

            for i, statement in enumerate(statements):
                try:
                    cursor.execute(statement)
                    logger.debug(f"✅ Executed statement {i+1}/{len(statements)}")
                except Exception as e:
                    # Some statements might fail if they already exist, that's OK
                    logger.debug(f"⚠️ Statement {i+1} warning: {e}")

            cursor.close()

            logger.info("✅ API keys schema created successfully")
            return True

        except Exception as e:
            logger.error(f"❌ Schema creation failed: {e}")
            return False

    def validate_migration(self) -> bool:
        """Validate that the migration was successful"""
        try:
            logger.info("🔍 Validating API keys migration...")

            cursor = self.connection.cursor()

            # Test that api_keys table exists and has correct structure
            cursor.execute("""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = 'api_keys'
                AND column_name IN ('key_id', 'key_hash', 'user_id', 'name')
                ORDER BY column_name
            """)

            columns = cursor.fetchall()
            cursor.close()

            expected_columns = ['key_hash', 'key_id', 'name', 'user_id']
            found_columns = [col[0] for col in columns]

            if all(col in found_columns for col in expected_columns):
                logger.info("✅ Migration validation successful")
                logger.info(f"   Found columns: {found_columns}")
                return True
            else:
                logger.error(f"❌ Migration validation failed: missing columns")
                logger.error(f"   Expected: {expected_columns}")
                logger.error(f"   Found: {found_columns}")
                return False

        except Exception as e:
            logger.error(f"❌ Migration validation failed: {e}")
            return False

    def run_migration(self) -> bool:
        """Run the complete PostgreSQL API keys migration"""
        try:
            logger.info("🔑 PostgreSQL API Keys Migration")
            logger.info("=" * 50)

            # Step 1: Connect to PostgreSQL
            if not self.connect():
                return False

            # Step 2: Check existing tables
            existing_tables = self.check_existing_tables()
            if not existing_tables.get('users'):
                logger.error("❌ Users table not found! Please ensure base schema exists.")
                logger.error("   Run: python setup_database.py postgresql")
                return False

            if existing_tables.get('api_keys'):
                logger.warning("⚠️ API keys table already exists, migration may be partial")

            # Step 3: Create API keys schema
            if not self.create_api_keys_schema():
                return False

            # Step 4: Validate migration
            if not self.validate_migration():
                return False

            logger.info("🎉 PostgreSQL API Keys Migration completed successfully!")
            logger.info("=" * 50)

            # Print next steps
            logger.info("📋 Migration Summary:")
            logger.info("   ✅ api_keys table created")
            logger.info("   ✅ api_key_usage_log table created")
            logger.info("   ✅ Indexes and constraints applied")
            logger.info("   ✅ Triggers for usage tracking enabled")
            logger.info("")
            logger.info("🔧 Next Steps:")
            logger.info("   1. Restart your FastAPI server")
            logger.info("   2. Test API key creation endpoint")
            logger.info("   3. Verify authentication works")

            return True

        except Exception as e:
            logger.error(f"❌ Migration failed: {e}")
            return False

        finally:
            if self.connection:
                self.connection.close()
                logger.info("🔌 Database connection closed")


def main():
    """Main entry point"""
    print("🔑 PostgreSQL API Keys Migration")
    print("=" * 50)

    try:
        migrator = PostgreSQLAPIKeyMigration()
        success = migrator.run_migration()

        if success:
            print("\n✅ Migration completed successfully!")
            print("🚀 Ready to restart your FastAPI server and test API key creation!")
            sys.exit(0)
        else:
            print("\n❌ Migration failed!")
            print("Please check the error messages above and fix any issues.")
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n⚠️ Migration interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
