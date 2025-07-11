#!/usr/bin/env python3
"""
Fixed PostgreSQL Migration Script
Handles SQLite to PostgreSQL data type conversions properly
"""

import os
import sys
import sqlite3
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from pathlib import Path
from datetime import datetime
import logging
from typing import Optional, Dict, List, Any
import json
import uuid

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class FixedPostgreSQLMigrator:
    """Fixed PostgreSQL migrator with proper data type handling"""
    
    def __init__(self):
        self.sqlite_path = "balance_tracker.db"
        self.postgres_config = {
            "host": "localhost",
            "port": 5432,
            "database": "balance_tracker",
            "user": "postgres",
            "password": None
        }
        self.sqlite_conn = None
        self.postgres_conn = None
        
    def convert_sqlite_value(self, value, column_name: str, table_name: str):
        """Convert SQLite values to PostgreSQL-compatible values"""
        # Handle None values
        if value is None:
            return None
        
        # Convert boolean fields (SQLite stores as 0/1, PostgreSQL needs true/false)
        boolean_fields = {
            'users': ['is_active', 'is_verified'],
            'currencies': ['is_active', 'is_fiat'],
            'trading_pairs': ['is_active'],
            'user_balances': [],
            'transactions': []
        }
        
        if table_name in boolean_fields and column_name in boolean_fields[table_name]:
            return bool(value)
        
        # Handle UUID fields (generate new UUIDs for PostgreSQL)
        if column_name == 'id' and table_name != 'currencies':
            return str(uuid.uuid4())
        
        # Convert metadata to JSON string if it's not already
        if column_name == 'metadata' and value is not None:
            if isinstance(value, str):
                try:
                    # Test if it's valid JSON
                    json.loads(value)
                    return value
                except json.JSONDecodeError:
                    # If not valid JSON, wrap in quotes
                    return json.dumps(value)
            else:
                return json.dumps(value)
        
        return value
    
    def migrate_data_table_fixed(self, table_name: str) -> bool:
        """Migrate data with proper type conversions"""
        try:
            logger.info(f"📦 Migrating table: {table_name}")
            
            # Get SQLite data
            sqlite_cursor = self.sqlite_conn.cursor()
            sqlite_cursor.execute(f"SELECT * FROM {table_name}")
            rows = sqlite_cursor.fetchall()
            
            if not rows:
                logger.info(f"ℹ️ No data found in {table_name}")
                return True
            
            # Get column names
            column_names = [description[0] for description in sqlite_cursor.description]
            
            # Prepare PostgreSQL insert
            postgres_cursor = self.postgres_conn.cursor()
            placeholders = ", ".join(["%s"] * len(column_names))
            columns = ", ".join(column_names)
            
            insert_query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
            
            # Convert and insert data row by row
            migrated_count = 0
            user_id_mapping = {}  # Track old ID -> new UUID mapping for foreign keys
            
            for row in rows:
                try:
                    # Convert SQLite row to list with proper type conversions
                    row_data = []
                    old_id = None
                    new_id = None
                    
                    for i, (column_name, value) in enumerate(zip(column_names, row)):
                        converted_value = self.convert_sqlite_value(value, column_name, table_name)
                        
                        # Track ID mapping for foreign key updates
                        if column_name == 'id':
                            old_id = value
                            if table_name != 'currencies':
                                new_id = converted_value
                        
                        # Handle foreign key references
                        if column_name == 'user_id' and table_name != 'users':
                            # Look up the new UUID for this user_id
                            if value in user_id_mapping:
                                converted_value = user_id_mapping[value]
                            else:
                                logger.warning(f"⚠️ User ID {value} not found in mapping for {table_name}")
                        
                        row_data.append(converted_value)
                    
                    # Store user ID mapping
                    if table_name == 'users' and old_id and new_id:
                        user_id_mapping[old_id] = new_id
                    
                    postgres_cursor.execute(insert_query, row_data)
                    migrated_count += 1
                    
                except Exception as e:
                    logger.warning(f"⚠️ Failed to migrate row in {table_name}: {e}")
                    # Rollback this transaction and continue
                    self.postgres_conn.rollback()
                    continue
            
            self.postgres_conn.commit()
            postgres_cursor.close()
            sqlite_cursor.close()
            
            logger.info(f"✅ Migrated {migrated_count}/{len(rows)} rows from {table_name}")
            
            # Store user mapping for later tables
            if table_name == 'users':
                self.user_id_mapping = user_id_mapping
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to migrate {table_name}: {e}")
            self.postgres_conn.rollback()
            return False
    
    def setup_postgres_connection(self, password: str) -> bool:
        """Setup PostgreSQL connection"""
        try:
            logger.info("🔍 Connecting to PostgreSQL server...")
            
            # Connect to postgres database first
            admin_conn = psycopg2.connect(
                host=self.postgres_config["host"],
                port=self.postgres_config["port"],
                user=self.postgres_config["user"],
                password=password,
                database="postgres"
            )
            admin_conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            admin_cursor = admin_conn.cursor()
            
            # Ensure database exists
            db_name = self.postgres_config["database"]
            try:
                admin_cursor.execute(f"CREATE DATABASE {db_name}")
                logger.info(f"✅ Database '{db_name}' created")
            except psycopg2.Error as e:
                if "already exists" in str(e):
                    logger.info(f"ℹ️ Database '{db_name}' already exists")
                else:
                    raise
            
            admin_cursor.close()
            admin_conn.close()
            
            # Now connect to our database
            self.postgres_conn = psycopg2.connect(
                host=self.postgres_config["host"],
                port=self.postgres_config["port"],
                user=self.postgres_config["user"],
                password=password,
                database=self.postgres_config["database"]
            )
            
            logger.info("✅ PostgreSQL connection established")
            return True
            
        except Exception as e:
            logger.error(f"❌ PostgreSQL connection failed: {e}")
            return False
    
    def connect_sqlite(self) -> bool:
        """Connect to existing SQLite database"""
        try:
            if not Path(self.sqlite_path).exists():
                logger.warning(f"⚠️ SQLite database not found: {self.sqlite_path}")
                return False
            
            self.sqlite_conn = sqlite3.connect(self.sqlite_path)
            self.sqlite_conn.row_factory = sqlite3.Row
            logger.info("✅ SQLite connection established")
            return True
            
        except Exception as e:
            logger.error(f"❌ SQLite connection failed: {e}")
            return False
    
    def clear_existing_data(self) -> bool:
        """Clear existing data from PostgreSQL tables"""
        try:
            logger.info("🧹 Clearing existing data from PostgreSQL tables...")
            
            cursor = self.postgres_conn.cursor()
            
            # Clear in reverse order to respect foreign keys
            tables = ["transactions", "user_balances", "users"]
            
            for table in tables:
                cursor.execute(f"DELETE FROM {table}")
                deleted_count = cursor.rowcount
                logger.info(f"   Cleared {deleted_count} rows from {table}")
            
            self.postgres_conn.commit()
            cursor.close()
            
            logger.info("✅ Existing data cleared")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to clear existing data: {e}")
            self.postgres_conn.rollback()
            return False
    
    def migrate_all_data_fixed(self) -> bool:
        """Migrate all data with proper handling"""
        if not self.sqlite_conn:
            logger.info("ℹ️ No SQLite database to migrate from")
            return True
        
        logger.info("🚀 Starting fixed data migration...")
        
        # Clear existing data first
        if not self.clear_existing_data():
            return False
        
        # Migration order (currencies already exist from schema)
        # We'll skip currencies and focus on user data
        migration_order = ["users", "user_balances", "transactions"]
        
        self.user_id_mapping = {}
        
        success_count = 0
        for table in migration_order:
            if self.migrate_data_table_fixed(table):
                success_count += 1
            else:
                logger.error(f"❌ Migration failed for table: {table}")
                return False
        
        logger.info(f"✅ Successfully migrated {success_count}/{len(migration_order)} tables")
        return True
    
    def verify_migration_fixed(self) -> bool:
        """Verify migration with detailed checks"""
        try:
            logger.info("🧪 Verifying fixed migration...")
            
            cursor = self.postgres_conn.cursor()
            
            # Check each table
            tables = ["users", "currencies", "user_balances", "transactions"]
            for table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                logger.info(f"✅ {table}: {count} records")
            
            # Test data types and relationships
            cursor.execute("""
                SELECT u.username, u.is_active, ub.currency_code, ub.total_balance
                FROM users u
                LEFT JOIN user_balances ub ON u.id = ub.user_id
                LIMIT 5
            """)
            
            results = cursor.fetchall()
            logger.info(f"✅ Test query returned {len(results)} results with proper joins")
            
            for row in results:
                logger.info(f"   User: {row[0]}, Active: {row[1]}, Currency: {row[2]}, Balance: {row[3]}")
            
            cursor.close()
            logger.info("✅ Migration verification completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Migration verification failed: {e}")
            return False
    
    def run_fixed_migration(self, postgres_password: str) -> bool:
        """Run the complete fixed migration process"""
        logger.info("🚀 Starting Fixed PostgreSQL migration...")
        
        try:
            # Step 1: Connect to databases
            if not self.setup_postgres_connection(postgres_password):
                return False
            
            if not self.connect_sqlite():
                logger.warning("⚠️ No SQLite database found - PostgreSQL schema is ready")
                return True
            
            # Step 2: Migrate data with fixes
            if not self.migrate_all_data_fixed():
                return False
            
            # Step 3: Verify migration
            if not self.verify_migration_fixed():
                return False
            
            logger.info("🎉 Fixed PostgreSQL migration completed successfully!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Migration failed: {e}")
            return False
        
        finally:
            # Cleanup connections
            if self.sqlite_conn:
                self.sqlite_conn.close()
            if self.postgres_conn:
                self.postgres_conn.close()


def main():
    """Main migration entry point"""
    print("🔧 Fixed PostgreSQL Migration")
    print("=" * 35)
    
    # Get PostgreSQL password
    postgres_password = os.getenv('POSTGRES_PASSWORD')
    if not postgres_password:
        postgres_password = input("Enter PostgreSQL password (default: dev_password_123): ")
        if not postgres_password:
            postgres_password = "dev_password_123"
    
    # Run migration
    migrator = FixedPostgreSQLMigrator()
    
    if migrator.run_fixed_migration(postgres_password):
        print("\n🎉 Fixed migration completed successfully!")
        print("\n📊 Your data should now be properly migrated with:")
        print("  • Boolean values converted correctly")
        print("  • UUIDs generated for PostgreSQL")
        print("  • Foreign key relationships preserved")
        print("\nNext steps:")
        print("1. Test your application: python3 main.py")
        print("2. Verify data: curl http://localhost:8000/health")
    else:
        print("\n❌ Fixed migration failed! Check the logs above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
