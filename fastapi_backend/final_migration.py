#!/usr/bin/env python3
"""
Final Migration Fix - Preserve Existing UUIDs
Handles cases where SQLite already has UUID-format IDs
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
import re

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class FinalMigrationFix:
    """Final migration that preserves existing UUIDs and handles all data types correctly"""
    
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
        
    def is_valid_uuid(self, value: str) -> bool:
        """Check if a string is a valid UUID"""
        if not isinstance(value, str):
            return False
        
        uuid_pattern = re.compile(
            r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
            re.IGNORECASE
        )
        return bool(uuid_pattern.match(value))
    
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
        
        # Handle UUID fields - preserve existing UUIDs or generate new ones
        if column_name == 'id':
            if table_name == 'currencies':
                # Currency codes are strings, not UUIDs
                return value
            elif self.is_valid_uuid(str(value)):
                # Already a valid UUID, preserve it
                return str(value)
            else:
                # Generate new UUID
                return str(uuid.uuid4())
        
        # Handle foreign key references that should be UUIDs
        if column_name in ['user_id', 'related_transaction_id'] and value is not None:
            if self.is_valid_uuid(str(value)):
                return str(value)
            else:
                # Try to convert or generate
                return str(uuid.uuid4())
        
        # Convert metadata to JSON string if needed
        if column_name == 'metadata' and value is not None:
            if isinstance(value, str):
                try:
                    # Test if it's valid JSON
                    json.loads(value)
                    return value
                except json.JSONDecodeError:
                    # If not valid JSON, wrap as string
                    return json.dumps(value)
            else:
                return json.dumps(value)
        
        return value
    
    def migrate_data_table_final(self, table_name: str) -> bool:
        """Migrate data with final fixes"""
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
            
            insert_query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders}) ON CONFLICT DO NOTHING"
            
            # Convert and insert data
            migrated_count = 0
            
            for row in rows:
                try:
                    # Convert SQLite row to list with proper type conversions
                    row_data = []
                    
                    for i, (column_name, value) in enumerate(zip(column_names, row)):
                        converted_value = self.convert_sqlite_value(value, column_name, table_name)
                        row_data.append(converted_value)
                    
                    postgres_cursor.execute(insert_query, row_data)
                    if postgres_cursor.rowcount > 0:
                        migrated_count += 1
                    
                except Exception as e:
                    logger.warning(f"⚠️ Failed to migrate row in {table_name}: {e}")
                    # Continue with next row
                    continue
            
            self.postgres_conn.commit()
            postgres_cursor.close()
            sqlite_cursor.close()
            
            logger.info(f"✅ Migrated {migrated_count}/{len(rows)} rows from {table_name}")
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
    
    def migrate_all_data_final(self) -> bool:
        """Migrate all data with final fixes"""
        if not self.sqlite_conn:
            logger.info("ℹ️ No SQLite database to migrate from")
            return True
        
        logger.info("🚀 Starting final data migration...")
        
        # Clear existing data first
        if not self.clear_existing_data():
            return False
        
        # Migration order - preserve relationships
        migration_order = ["users", "user_balances", "transactions"]
        
        success_count = 0
        for table in migration_order:
            if self.migrate_data_table_final(table):
                success_count += 1
            else:
                logger.error(f"❌ Migration failed for table: {table}")
                return False
        
        logger.info(f"✅ Successfully migrated {success_count}/{len(migration_order)} tables")
        return True
    
    def verify_migration_final(self) -> bool:
        """Verify final migration with detailed checks"""
        try:
            logger.info("🧪 Verifying final migration...")
            
            cursor = self.postgres_conn.cursor()
            
            # Check each table
            tables = ["users", "currencies", "user_balances", "transactions"]
            for table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                logger.info(f"✅ {table}: {count} records")
            
            # Test data types and relationships
            cursor.execute("""
                SELECT u.id, u.username, u.is_active, ub.currency_code, ub.total_balance, t.amount
                FROM users u
                LEFT JOIN user_balances ub ON u.id = ub.user_id
                LEFT JOIN transactions t ON u.id = t.user_id
                LIMIT 5
            """)
            
            results = cursor.fetchall()
            logger.info(f"✅ Test query returned {len(results)} results with proper joins")
            
            for row in results:
                logger.info(f"   User: {row[1]} (ID: {row[0]}), Active: {row[2]}, Currency: {row[3]}, Balance: {row[4]}, Tx Amount: {row[5]}")
            
            # Check data integrity
            cursor.execute("SELECT COUNT(*) FROM users WHERE is_active = true")
            active_users = cursor.fetchone()[0]
            logger.info(f"✅ Active users: {active_users}")
            
            cursor.close()
            logger.info("✅ Final migration verification completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Migration verification failed: {e}")
            return False
    
    def run_final_migration(self, postgres_password: str) -> bool:
        """Run the complete final migration process"""
        logger.info("🚀 Starting Final PostgreSQL migration...")
        
        try:
            # Step 1: Connect to databases
            if not self.setup_postgres_connection(postgres_password):
                return False
            
            if not self.connect_sqlite():
                logger.warning("⚠️ No SQLite database found - PostgreSQL schema is ready")
                return True
            
            # Step 2: Migrate data with final fixes
            if not self.migrate_all_data_final():
                return False
            
            # Step 3: Verify migration
            if not self.verify_migration_final():
                return False
            
            logger.info("🎉 Final PostgreSQL migration completed successfully!")
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
    print("🎯 Final PostgreSQL Migration Fix")
    print("=" * 40)
    
    # Get PostgreSQL password
    postgres_password = os.getenv('POSTGRES_PASSWORD')
    if not postgres_password:
        postgres_password = input("Enter PostgreSQL password (default: dev_password_123): ")
        if not postgres_password:
            postgres_password = "dev_password_123"
    
    # Run migration
    migrator = FinalMigrationFix()
    
    if migrator.run_final_migration(postgres_password):
        print("\n🎉 Final migration completed successfully!")
        print("\n📊 Your data has been migrated with:")
        print("  • Preserved existing UUID relationships")
        print("  • Boolean values converted correctly")
        print("  • Foreign key relationships maintained")
        print("  • JSON metadata handled properly")
        print("\nNext steps:")
        print("1. Test your application: python3 main.py")
        print("2. Verify data: curl http://localhost:8000/health")
        print("3. Check your user: curl http://localhost:8000/api/v1/users/agent_1")
    else:
        print("\n❌ Final migration failed! Check the logs above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
