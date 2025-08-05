#!/usr/bin/env python3
"""
Entity Management Database Migration Script - PostgreSQL Only
Task 1.1: Creates entities and entity_memberships tables for entity-based user management

This script adds:
1. entities table - stores trading entities/organizations
2. entity_memberships table - links users to entities with specific roles
3. Proper indexes and constraints for performance and data integrity

Production PostgreSQL only - no SQLite support.
"""

import os
import sys
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Dict
import psycopg2

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class EntityMigration:
    """Handles entity tables creation and migration for PostgreSQL"""

    def __init__(self):
        self.database_url = os.getenv('DATABASE_URL', 'postgresql://localhost:5432/balance_tracker')
        self.connection = None

        # Ensure PostgreSQL URL
        if not self.database_url.startswith(('postgresql', 'postgres')):
            raise ValueError(f"Production requires PostgreSQL database. Got: {self.database_url}")

    def get_postgresql_schema(self) -> str:
        """PostgreSQL schema for entities tables"""
        return """
-- Entity Management Tables for PostgreSQL
-- Supports multi-tenant entity-based access control

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Entities Table - Trading organizations/companies
CREATE TABLE IF NOT EXISTS entities (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL,                      -- Entity name (e.g., "Acme Trading LLC")
    code VARCHAR(20) UNIQUE NOT NULL,                -- Short code (e.g., "ACME", "ABC_CORP")
    description TEXT,                                -- Optional description
    entity_type VARCHAR(20) DEFAULT 'trading_entity', -- Type: trading_entity, fund, institution
    contact_email VARCHAR(255),                      -- Primary contact email
    contact_phone VARCHAR(50),                       -- Contact phone number
    address TEXT,                                    -- Physical address
    tax_id VARCHAR(50),                              -- Tax ID or registration number
    is_active BOOLEAN DEFAULT true,                  -- Can be deactivated
    created_by UUID REFERENCES users(id),           -- Admin who created the entity
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- Constraints
    CONSTRAINT entities_name_length CHECK (LENGTH(name) >= 2),
    CONSTRAINT entities_code_format CHECK (code ~ '^[A-Z0-9_]{2,20}$'),
    CONSTRAINT entities_type_valid CHECK (entity_type IN ('trading_entity', 'fund', 'institution', 'individual'))
);

-- Entity Memberships Table - Links users to entities with specific roles
CREATE TABLE IF NOT EXISTS entity_memberships (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    entity_id UUID NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    entity_role VARCHAR(20) NOT NULL,               -- Role within this entity: trader, viewer
    is_active BOOLEAN DEFAULT true,                 -- Can be deactivated without deletion
    created_by UUID REFERENCES users(id),          -- Admin who created the membership
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- Constraints
    CONSTRAINT entity_memberships_role_valid CHECK (entity_role IN ('trader', 'viewer')),
    CONSTRAINT entity_memberships_unique UNIQUE (entity_id, user_id)
);

-- Indexes for entities table
CREATE INDEX IF NOT EXISTS idx_entities_code ON entities(code);
CREATE INDEX IF NOT EXISTS idx_entities_name ON entities(name);
CREATE INDEX IF NOT EXISTS idx_entities_active ON entities(is_active);
CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(entity_type);

-- Indexes for entity_memberships table
CREATE INDEX IF NOT EXISTS idx_entity_memberships_entity_id ON entity_memberships(entity_id);
CREATE INDEX IF NOT EXISTS idx_entity_memberships_user_id ON entity_memberships(user_id);
CREATE INDEX IF NOT EXISTS idx_entity_memberships_active ON entity_memberships(is_active);
CREATE INDEX IF NOT EXISTS idx_entity_memberships_role ON entity_memberships(entity_role);

-- Update trigger for entities
CREATE OR REPLACE FUNCTION update_entities_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_entities_updated_at
    BEFORE UPDATE ON entities
    FOR EACH ROW
    EXECUTE FUNCTION update_entities_updated_at();

-- Update trigger for entity_memberships
CREATE OR REPLACE FUNCTION update_entity_memberships_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_entity_memberships_updated_at
    BEFORE UPDATE ON entity_memberships
    FOR EACH ROW
    EXECUTE FUNCTION update_entity_memberships_updated_at();

-- Insert default system entity for existing users
INSERT INTO entities (name, code, description, entity_type, is_active, created_at)
VALUES (
    'System Default Entity',
    'SYSTEM_DEFAULT',
    'Default entity for existing users during migration',
    'trading_entity',
    true,
    CURRENT_TIMESTAMP
) ON CONFLICT (code) DO NOTHING;
"""

    def connect(self) -> bool:
        """Connect to PostgreSQL database"""
        try:
            logger.info("Connecting to PostgreSQL database...")

            self.connection = psycopg2.connect(self.database_url)
            self.connection.autocommit = True

            logger.info("✅ Connected to PostgreSQL database")
            return True

        except Exception as e:
            logger.error(f"❌ PostgreSQL connection failed: {e}")
            return False

    def disconnect(self):
        """Disconnect from database"""
        if self.connection:
            self.connection.close()
            logger.info("Database connection closed")

    def check_existing_tables(self) -> Dict[str, bool]:
        """Check if required tables exist in PostgreSQL"""
        try:
            cursor = self.connection.cursor()

            cursor.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name IN ('users', 'entities', 'entity_memberships')
                ORDER BY table_name
            """)

            existing_tables = [row[0] for row in cursor.fetchall()]
            cursor.close()

            result = {
                'users': 'users' in existing_tables,
                'entities': 'entities' in existing_tables,
                'entity_memberships': 'entity_memberships' in existing_tables,
                'all_tables': existing_tables
            }

            logger.info(f"📊 Existing tables: {result['all_tables']}")
            return result

        except Exception as e:
            logger.error(f"❌ Failed to check existing tables: {e}")
            return {}

    def create_entity_schema(self) -> bool:
        """Create entity tables in PostgreSQL"""
        try:
            schema_sql = self.get_postgresql_schema()

            logger.info("🏗️  Creating entity management schema...")

            cursor = self.connection.cursor()
            cursor.execute(schema_sql)
            self.connection.commit()
            cursor.close()

            logger.info("✅ Entity schema created successfully")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to create entity schema: {e}")
            return False

    def migrate_existing_users(self) -> bool:
        """Migrate existing users to default entity"""
        try:
            logger.info("🔄 Migrating existing users to default entity...")

            cursor = self.connection.cursor()

            # Get default entity ID
            cursor.execute("SELECT id FROM entities WHERE code = 'SYSTEM_DEFAULT'")
            entity_result = cursor.fetchone()
            if not entity_result:
                logger.error("❌ Default entity not found")
                return False

            default_entity_id = entity_result[0]
            logger.info(f"📌 Default entity ID: {default_entity_id}")

            # Get all users who don't have admin role
            cursor.execute("""
                SELECT id, username, COALESCE(role, 'trader') as role
                FROM users
                WHERE COALESCE(role, 'trader') != 'admin'
            """)

            users_to_migrate = cursor.fetchall()
            logger.info(f"Found {len(users_to_migrate)} users to migrate")

            # Insert entity memberships for non-admin users
            migrated_count = 0
            for user in users_to_migrate:
                user_id, username, user_role = user

                # Map user role to entity role (trader stays trader, viewer stays viewer)
                entity_role = 'trader' if user_role == 'trader' else 'viewer'

                try:
                    cursor.execute("""
                        INSERT INTO entity_memberships (entity_id, user_id, entity_role, is_active, created_at)
                        VALUES (%s, %s, %s, true, CURRENT_TIMESTAMP)
                        ON CONFLICT (entity_id, user_id) DO NOTHING
                    """, (default_entity_id, user_id, entity_role))

                    migrated_count += 1
                    logger.debug(f"✅ Migrated user {username} ({user_role} -> {entity_role})")

                except Exception as e:
                    logger.warning(f"⚠️  Failed to migrate user {username}: {e}")

            self.connection.commit()
            cursor.close()
            logger.info(f"✅ Successfully migrated {migrated_count} users to default entity")
            return True

        except Exception as e:
            logger.error(f"❌ User migration failed: {e}")
            return False

    def validate_migration(self) -> bool:
        """Validate the migration was successful"""
        try:
            logger.info("🔍 Validating entity migration...")

            cursor = self.connection.cursor()

            # Check entities table has default entity
            cursor.execute("SELECT COUNT(*) FROM entities WHERE code = 'SYSTEM_DEFAULT'")
            entity_count = cursor.fetchone()[0]

            if entity_count != 1:
                logger.error(f"❌ Expected 1 default entity, found {entity_count}")
                return False

            # Check entity_memberships table has records
            cursor.execute("SELECT COUNT(*) FROM entity_memberships")
            membership_count = cursor.fetchone()[0]

            # Check users without admin role have memberships
            cursor.execute("""
                SELECT COUNT(*)
                FROM users u
                LEFT JOIN entity_memberships em ON u.id = em.user_id
                WHERE COALESCE(u.role, 'trader') != 'admin' AND em.user_id IS NULL
            """)

            orphaned_users = cursor.fetchone()[0]

            cursor.close()

            logger.info(f"📊 Validation results:")
            logger.info(f"   - Default entities: {entity_count}")
            logger.info(f"   - Entity memberships: {membership_count}")
            logger.info(f"   - Orphaned non-admin users: {orphaned_users}")

            if orphaned_users > 0:
                logger.warning(f"⚠️  {orphaned_users} non-admin users not assigned to entities")
                return False

            logger.info("✅ Migration validation successful")
            return True

        except Exception as e:
            logger.error(f"❌ Migration validation failed: {e}")
            return False

    def run_migration(self) -> bool:
        """Run the complete entity migration"""
        try:
            logger.info("🏢 Entity Management Database Migration")
            logger.info("=" * 50)

            # Step 1: Connect to database
            if not self.connect():
                return False

            # Step 2: Check existing tables
            existing_tables = self.check_existing_tables()
            if not existing_tables.get('users'):
                logger.error("❌ Users table not found! Please ensure base schema exists.")
                return False

            if existing_tables.get('entities') and existing_tables.get('entity_memberships'):
                logger.warning("⚠️  Entity tables already exist, migration may be partial")

            # Step 3: Create entity schema
            if not self.create_entity_schema():
                return False

            # Step 4: Migrate existing users
            if not self.migrate_existing_users():
                return False

            # Step 5: Validate migration
            if not self.validate_migration():
                return False

            logger.info("🎉 Entity Management Migration completed successfully!")
            logger.info("=" * 50)

            # Print summary
            logger.info("📋 Migration Summary:")
            logger.info("   ✅ entities table created")
            logger.info("   ✅ entity_memberships table created")
            logger.info("   ✅ Indexes and constraints applied")
            logger.info("   ✅ Default entity created")
            logger.info("   ✅ Existing users migrated")
            logger.info("")
            logger.info("🔧 Next Steps:")
            logger.info("   1. Update authentication system for entity scope")
            logger.info("   2. Create entity management API endpoints")
            logger.info("   3. Test entity-based access control")

            return True

        except Exception as e:
            logger.error(f"❌ Migration failed: {e}")
            return False

        finally:
            self.disconnect()


def main():
    """Main migration function"""
    parser = argparse.ArgumentParser(description='Entity Management Database Migration')
    parser.add_argument('--database-url',
                       help='Database URL (overrides environment variable)')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be done without making changes')

    args = parser.parse_args()

    if args.database_url:
        os.environ['DATABASE_URL'] = args.database_url

    if args.dry_run:
        logger.info("🔍 DRY RUN MODE - No changes will be made")
        logger.info("This would create entity management tables and migrate existing users")
        return True

    # Run the migration
    migrator = EntityMigration()
    success = migrator.run_migration()

    if success:
        logger.info("✅ Entity migration completed successfully!")
        return True
    else:
        logger.error("❌ Entity migration failed!")
        return False


if __name__ == "__main__":
    import argparse
    success = main()
    sys.exit(0 if success else 1)
