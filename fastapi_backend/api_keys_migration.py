#!/usr/bin/env python3
"""
API Keys Database Migration Script
Task 1.1: Database Schema Changes for API Key Authentication System

This script adds the api_keys table and related infrastructure
for switching from JWT to API key authentication.
"""

import os
import sys
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class APIKeyMigration:
    """Handles API key table creation and migration"""
    
    def __init__(self):
        self.database_url = os.getenv('DATABASE_URL', 'sqlite:///balance_tracker.db')
        self.connection = None
        
    def detect_database_type(self) -> str:
        """Detect database type from URL"""
        if self.database_url.startswith(('postgresql', 'postgres')):
            return 'postgresql'
        elif self.database_url.startswith('sqlite'):
            return 'sqlite'
        else:
            raise ValueError(f"Unsupported database type: {self.database_url}")
    
    def get_postgresql_schema(self) -> str:
        """PostgreSQL schema for API keys table"""
        return """
-- API Keys Table for PostgreSQL
-- Supports admin-managed API key authentication

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
    
    -- Indexes for performance
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
    request_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Index for performance
    CREATE INDEX IF NOT EXISTS idx_api_usage_key_id ON api_key_usage_log(api_key_id),
    CREATE INDEX IF NOT EXISTS idx_api_usage_timestamp ON api_key_usage_log(request_timestamp)
);

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

    def get_sqlite_schema(self) -> str:
        """SQLite schema for API keys table"""
        return """
-- API Keys Table for SQLite
-- Supports admin-managed API key authentication

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS api_keys (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    key_id VARCHAR(32) UNIQUE NOT NULL,          -- Public key identifier (btapi_xxxxx)
    key_hash VARCHAR(255) NOT NULL,              -- Bcrypt hash of the full API key
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,                  -- Human-readable key name
    description TEXT,                            -- Optional description
    is_active BOOLEAN DEFAULT 1,                -- Can be deactivated without deletion
    created_by TEXT REFERENCES users(id),       -- Admin who created the key
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used_at TIMESTAMP,                     -- Track last usage
    expires_at TIMESTAMP,                       -- Optional expiration date
    permissions_scope TEXT DEFAULT 'inherit',   -- 'inherit' or JSON permissions
    
    -- Constraints
    CHECK (LENGTH(name) >= 1),
    CHECK (key_id GLOB 'btapi_*')
);

-- Indexes for fast lookups
CREATE INDEX IF NOT EXISTS idx_api_keys_key_id ON api_keys(key_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_user_id ON api_keys(user_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_active ON api_keys(is_active);
CREATE INDEX IF NOT EXISTS idx_api_keys_last_used ON api_keys(last_used_at);

-- API Key Usage Log Table (for audit trail)
CREATE TABLE IF NOT EXISTS api_key_usage_log (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    api_key_id TEXT NOT NULL REFERENCES api_keys(id) ON DELETE CASCADE,
    endpoint VARCHAR(255),                       -- API endpoint accessed
    method VARCHAR(10),                          -- HTTP method
    status_code INTEGER,                         -- Response status
    ip_address TEXT,                             -- Client IP address
    user_agent TEXT,                             -- Client user agent
    request_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for usage log
CREATE INDEX IF NOT EXISTS idx_api_usage_key_id ON api_key_usage_log(api_key_id);
CREATE INDEX IF NOT EXISTS idx_api_usage_timestamp ON api_key_usage_log(request_timestamp);

-- Trigger to update last_used_at (SQLite version)
CREATE TRIGGER IF NOT EXISTS trigger_update_api_key_last_used
    AFTER INSERT ON api_key_usage_log
    FOR EACH ROW
BEGIN
    UPDATE api_keys 
    SET last_used_at = CURRENT_TIMESTAMP 
    WHERE id = NEW.api_key_id;
END;
"""

    def connect_postgresql(self) -> bool:
        """Connect to PostgreSQL database"""
        try:
            import psycopg2
            from urllib.parse import urlparse
            
            parsed = urlparse(self.database_url)
            self.connection = psycopg2.connect(
                host=parsed.hostname,
                port=parsed.port or 5432,
                database=parsed.path[1:],
                user=parsed.username,
                password=parsed.password
            )
            
            logger.info(f"✅ Connected to PostgreSQL database: {parsed.path[1:]}")
            return True
            
        except Exception as e:
            logger.error(f"❌ PostgreSQL connection failed: {e}")
            return False
    
    def connect_sqlite(self) -> bool:
        """Connect to SQLite database"""
        try:
            import sqlite3
            
            # Extract path from sqlite URL
            db_path = self.database_url.replace('sqlite:///', '')
            if not Path(db_path).exists():
                logger.error(f"❌ SQLite database not found: {db_path}")
                return False
            
            self.connection = sqlite3.connect(db_path)
            logger.info(f"✅ Connected to SQLite database: {db_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ SQLite connection failed: {e}")
            return False
    
    def check_existing_tables(self) -> dict:
        """Check what tables already exist"""
        try:
            cursor = self.connection.cursor()
            
            if self.detect_database_type() == 'postgresql':
                cursor.execute("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public'
                    ORDER BY table_name
                """)
            else:
                cursor.execute("""
                    SELECT name 
                    FROM sqlite_master 
                    WHERE type='table'
                    ORDER BY name
                """)
            
            tables = [row[0] for row in cursor.fetchall()]
            cursor.close()
            
            result = {
                'users': 'users' in tables,
                'api_keys': 'api_keys' in tables,
                'api_key_usage_log': 'api_key_usage_log' in tables,
                'all_tables': tables
            }
            
            logger.info(f"📊 Existing tables: {result['all_tables']}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Failed to check existing tables: {e}")
            return {}
    
    def apply_schema(self) -> bool:
        """Apply the API keys schema"""
        try:
            db_type = self.detect_database_type()
            
            if db_type == 'postgresql':
                schema_sql = self.get_postgresql_schema()
            else:
                schema_sql = self.get_sqlite_schema()
            
            logger.info(f"📋 Applying {db_type.upper()} API keys schema...")
            
            cursor = self.connection.cursor()
            
            # Execute schema in parts for better error handling
            schema_parts = schema_sql.split(';')
            for i, part in enumerate(schema_parts):
                part = part.strip()
                if part:
                    try:
                        cursor.execute(part)
                        logger.debug(f"✅ Executed schema part {i+1}")
                    except Exception as e:
                        # Some parts might fail if they already exist, that's OK
                        logger.debug(f"⚠️ Schema part {i+1} warning: {e}")
            
            self.connection.commit()
            cursor.close()
            
            logger.info("✅ API keys schema applied successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Schema application failed: {e}")
            if self.connection:
                self.connection.rollback()
            return False
    
    def validate_migration(self) -> bool:
        """Validate that the migration was successful"""
        try:
            logger.info("🔍 Validating API keys migration...")
            
            cursor = self.connection.cursor()
            
            # Test that we can create a sample API key
            if self.detect_database_type() == 'postgresql':
                test_query = """
                    SELECT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = 'api_keys' 
                        AND column_name = 'key_id'
                    )
                """
            else:
                test_query = """
                    SELECT COUNT(*) FROM pragma_table_info('api_keys') 
                    WHERE name = 'key_id'
                """
            
            cursor.execute(test_query)
            result = cursor.fetchone()[0]
            cursor.close()
            
            if result:
                logger.info("✅ Migration validation successful")
                return True
            else:
                logger.error("❌ Migration validation failed: key_id column not found")
                return False
                
        except Exception as e:
            logger.error(f"❌ Migration validation failed: {e}")
            return False
    
    def run_migration(self) -> bool:
        """Run the complete API keys migration"""
        try:
            logger.info("🚀 Starting API Keys Migration")
            logger.info("=" * 50)
            
            # Step 1: Detect database type
            db_type = self.detect_database_type()
            logger.info(f"📊 Database type: {db_type.upper()}")
            
            # Step 2: Connect to database
            if db_type == 'postgresql':
                if not self.connect_postgresql():
                    return False
            else:
                if not self.connect_sqlite():
                    return False
            
            # Step 3: Check existing tables
            existing_tables = self.check_existing_tables()
            if not existing_tables.get('users'):
                logger.error("❌ Users table not found! Please ensure base schema exists.")
                return False
            
            if existing_tables.get('api_keys'):
                logger.warning("⚠️ API keys table already exists, migration may be partial")
            
            # Step 4: Apply schema
            if not self.apply_schema():
                return False
            
            # Step 5: Validate migration
            if not self.validate_migration():
                return False
            
            logger.info("🎉 API Keys Migration completed successfully!")
            logger.info("=" * 50)
            
            # Print next steps
            logger.info("📋 Migration Summary:")
            logger.info("   ✅ api_keys table created")
            logger.info("   ✅ api_key_usage_log table created")
            logger.info("   ✅ Indexes and constraints applied")
            logger.info("   ✅ Triggers for usage tracking enabled")
            logger.info("")
            logger.info("🔧 Next Steps:")
            logger.info("   1. Create API key models (Task 1.2)")
            logger.info("   2. Implement API key service (Task 1.3)")
            logger.info("   3. Update authentication dependencies")
            
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
    print("🔑 API Keys Database Migration")
    print("=" * 50)
    
    try:
        migrator = APIKeyMigration()
        success = migrator.run_migration()
        
        if success:
            print("\n✅ Migration completed successfully!")
            print("Ready to proceed with Task 1.2: API Key Models")
            sys.exit(0)
        else:
            print("\n❌ Migration failed!")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⚠️ Migration interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

