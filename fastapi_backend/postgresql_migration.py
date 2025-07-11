#!/usr/bin/env python3
"""
PostgreSQL Migration Script for FastAPI Balance Tracking System
Task 1.1: Database Migration to PostgreSQL

This script handles:
1. PostgreSQL setup and connection
2. Schema conversion from SQLite to PostgreSQL
3. Data migration from existing SQLite database
4. Configuration updates
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

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class PostgreSQLMigrator:
    """Handles migration from SQLite to PostgreSQL"""
    
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
        
    def get_postgres_schema(self) -> str:
        """PostgreSQL-compatible schema definition"""
        return """
-- PostgreSQL schema for Balance Tracking System
-- Converted from SQLite with production optimizations

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users Table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    is_active BOOLEAN DEFAULT true,
    is_verified BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP WITH TIME ZONE,
    CONSTRAINT users_username_length CHECK (LENGTH(username) >= 3),
    CONSTRAINT users_email_format CHECK (email ~* '^[^@]+@[^@]+\.[^@]+$')
);

-- Currencies Table
CREATE TABLE IF NOT EXISTS currencies (
    code VARCHAR(10) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    symbol VARCHAR(10),
    decimal_places INTEGER DEFAULT 8,
    is_active BOOLEAN DEFAULT true,
    is_fiat BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT currencies_decimal_places CHECK (decimal_places >= 0 AND decimal_places <= 18)
);

-- User Balances Table
CREATE TABLE IF NOT EXISTS user_balances (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    currency_code VARCHAR(10) NOT NULL REFERENCES currencies(code),
    total_balance DECIMAL(28, 18) DEFAULT 0 NOT NULL,
    available_balance DECIMAL(28, 18) DEFAULT 0 NOT NULL,
    locked_balance DECIMAL(28, 18) DEFAULT 0 NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, currency_code),
    CONSTRAINT balances_positive CHECK (total_balance >= 0),
    CONSTRAINT available_positive CHECK (available_balance >= 0),
    CONSTRAINT locked_positive CHECK (locked_balance >= 0),
    CONSTRAINT balance_equation CHECK (total_balance = available_balance + locked_balance)
);

-- Transactions Table
CREATE TABLE IF NOT EXISTS transactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id),
    external_id VARCHAR(255),
    transaction_type VARCHAR(20) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    amount DECIMAL(28, 18) NOT NULL,
    currency_code VARCHAR(10) NOT NULL REFERENCES currencies(code),
    fee_amount DECIMAL(28, 18) DEFAULT 0,
    fee_currency_code VARCHAR(10) REFERENCES currencies(code),
    balance_before DECIMAL(28, 18),
    balance_after DECIMAL(28, 18),
    description TEXT,
    metadata JSONB,
    related_transaction_id UUID REFERENCES transactions(id),
    external_reference VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP WITH TIME ZONE,
    CONSTRAINT transactions_amount_positive CHECK (amount > 0),
    CONSTRAINT transactions_fee_positive CHECK (fee_amount >= 0),
    CONSTRAINT transactions_type_valid CHECK (
        transaction_type IN ('deposit', 'withdrawal', 'trade_buy', 'trade_sell', 
                            'transfer_in', 'transfer_out', 'fee', 'adjustment')
    ),
    CONSTRAINT transactions_status_valid CHECK (
        status IN ('pending', 'processing', 'completed', 'failed', 'cancelled', 'rejected')
    )
);

-- Trading Pairs Table
CREATE TABLE IF NOT EXISTS trading_pairs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    base_currency VARCHAR(10) NOT NULL REFERENCES currencies(code),
    quote_currency VARCHAR(10) NOT NULL REFERENCES currencies(code),
    symbol VARCHAR(20) NOT NULL UNIQUE,
    min_trade_amount DECIMAL(28, 18) DEFAULT 0,
    max_trade_amount DECIMAL(28, 18),
    price_precision INTEGER DEFAULT 8,
    amount_precision INTEGER DEFAULT 8,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT trading_pairs_different_currencies CHECK (base_currency != quote_currency),
    CONSTRAINT trading_pairs_min_amount_positive CHECK (min_trade_amount >= 0)
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_active ON users(is_active);

CREATE INDEX IF NOT EXISTS idx_user_balances_user_id ON user_balances(user_id);
CREATE INDEX IF NOT EXISTS idx_user_balances_currency ON user_balances(currency_code);
CREATE INDEX IF NOT EXISTS idx_user_balances_user_currency ON user_balances(user_id, currency_code);

CREATE INDEX IF NOT EXISTS idx_transactions_user_id ON transactions(user_id);
CREATE INDEX IF NOT EXISTS idx_transactions_type ON transactions(transaction_type);
CREATE INDEX IF NOT EXISTS idx_transactions_status ON transactions(status);
CREATE INDEX IF NOT EXISTS idx_transactions_created_at ON transactions(created_at);
CREATE INDEX IF NOT EXISTS idx_transactions_currency ON transactions(currency_code);

CREATE INDEX IF NOT EXISTS idx_trading_pairs_symbol ON trading_pairs(symbol);
CREATE INDEX IF NOT EXISTS idx_trading_pairs_active ON trading_pairs(is_active);

-- Trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply triggers to all tables with updated_at
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    
CREATE TRIGGER update_currencies_updated_at BEFORE UPDATE ON currencies
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    
CREATE TRIGGER update_user_balances_updated_at BEFORE UPDATE ON user_balances
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    
CREATE TRIGGER update_transactions_updated_at BEFORE UPDATE ON transactions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    
CREATE TRIGGER update_trading_pairs_updated_at BEFORE UPDATE ON trading_pairs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert initial currency data
INSERT INTO currencies (code, name, symbol, decimal_places, is_fiat) VALUES
('USD', 'US Dollar', '$', 2, true),
('EUR', 'Euro', '€', 2, true),
('GBP', 'British Pound', '£', 2, true),
('BTC', 'Bitcoin', '₿', 8, false),
('ETH', 'Ethereum', 'Ξ', 8, false),
('LTC', 'Litecoin', 'Ł', 8, false),
('ADA', 'Cardano', '₳', 6, false),
('SOL', 'Solana', 'SOL', 6, false)
ON CONFLICT (code) DO NOTHING;

-- Insert trading pairs
INSERT INTO trading_pairs (base_currency, quote_currency, symbol, min_trade_amount, price_precision, amount_precision) VALUES
('BTC', 'USD', 'BTC/USD', 0.00001, 2, 8),
('ETH', 'USD', 'ETH/USD', 0.001, 2, 8),
('ETH', 'BTC', 'ETH/BTC', 0.001, 8, 8),
('LTC', 'USD', 'LTC/USD', 0.01, 2, 8),
('ADA', 'USD', 'ADA/USD', 1, 4, 6),
('SOL', 'USD', 'SOL/USD', 0.1, 2, 6)
ON CONFLICT (symbol) DO NOTHING;
"""

    def setup_postgres_connection(self, password: str) -> bool:
        """Setup PostgreSQL connection and create database if needed"""
        try:
            # First connect to postgres database to create our database
            logger.info("🔍 Connecting to PostgreSQL server...")
            
            admin_conn = psycopg2.connect(
                host=self.postgres_config["host"],
                port=self.postgres_config["port"],
                user=self.postgres_config["user"],
                password=password,
                database="postgres"
            )
            admin_conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            admin_cursor = admin_conn.cursor()
            
            # Create database if it doesn't exist
            db_name = self.postgres_config["database"]
            logger.info(f"🗄️ Creating database '{db_name}' if it doesn't exist...")
            
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
    
    def apply_postgres_schema(self) -> bool:
        """Apply PostgreSQL schema"""
        try:
            logger.info("📋 Applying PostgreSQL schema...")
            cursor = self.postgres_conn.cursor()
            cursor.execute(self.get_postgres_schema())
            self.postgres_conn.commit()
            cursor.close()
            logger.info("✅ PostgreSQL schema applied successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Schema application failed: {e}")
            self.postgres_conn.rollback()
            return False
    
    def migrate_data_table(self, table_name: str, column_mapping: Dict[str, str] = None) -> bool:
        """Migrate data from SQLite table to PostgreSQL"""
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
            
            # Apply column mapping if provided
            if column_mapping:
                column_names = [column_mapping.get(col, col) for col in column_names]
            
            # Prepare PostgreSQL insert
            postgres_cursor = self.postgres_conn.cursor()
            placeholders = ", ".join(["%s"] * len(column_names))
            columns = ", ".join(column_names)
            
            insert_query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
            
            # Convert and insert data
            migrated_count = 0
            for row in rows:
                try:
                    # Convert SQLite row to list and handle special cases
                    row_data = list(row)
                    
                    # Handle UUID conversion for PostgreSQL (if id field exists)
                    if 'id' in column_names and table_name != 'currencies':
                        # Generate new UUID for PostgreSQL
                        row_data[column_names.index('id')] = None  # Let PostgreSQL generate UUID
                    
                    postgres_cursor.execute(insert_query, row_data)
                    migrated_count += 1
                    
                except Exception as e:
                    logger.warning(f"⚠️ Failed to migrate row in {table_name}: {e}")
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
    
    def migrate_all_data(self) -> bool:
        """Migrate all data from SQLite to PostgreSQL"""
        logger.info("🚀 Starting data migration...")
        
        # Define migration order (respecting foreign key constraints)
        migration_order = [
            "currencies",
            "users", 
            "user_balances",
            "transactions",
            "trading_pairs"
        ]
        
        success_count = 0
        for table in migration_order:
            if self.migrate_data_table(table):
                success_count += 1
            else:
                logger.error(f"❌ Migration failed for table: {table}")
                return False
        
        logger.info(f"✅ Successfully migrated {success_count}/{len(migration_order)} tables")
        return True
    
    def update_environment_config(self, postgres_password: str) -> bool:
        """Update .env file with PostgreSQL configuration"""
        try:
            logger.info("⚙️ Updating environment configuration...")
            
            env_file = Path(".env")
            
            # Read existing .env if it exists
            env_content = ""
            if env_file.exists():
                env_content = env_file.read_text()
            
            # Create PostgreSQL configuration
            postgres_config = f"""
# Database Configuration - PostgreSQL (Updated by migration script)
DATABASE_URL=postgresql://{self.postgres_config['user']}:{postgres_password}@{self.postgres_config['host']}:{self.postgres_config['port']}/{self.postgres_config['database']}
DATABASE_TYPE=postgresql

# Migration completed on: {datetime.now().isoformat()}
"""
            
            # Replace or add database configuration
            lines = env_content.split('\n')
            new_lines = []
            in_db_section = False
            
            for line in lines:
                if line.startswith('DATABASE_URL') or line.startswith('DATABASE_TYPE'):
                    continue  # Skip old database config
                new_lines.append(line)
            
            # Add new database configuration at the beginning
            final_content = postgres_config + '\n' + '\n'.join(new_lines)
            
            # Write updated .env file
            env_file.write_text(final_content)
            
            logger.info("✅ Environment configuration updated")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to update environment config: {e}")
            return False
    
    def verify_migration(self) -> bool:
        """Verify migration was successful"""
        try:
            logger.info("🧪 Verifying migration...")
            
            cursor = self.postgres_conn.cursor()
            
            # Check each table has data
            tables = ["users", "currencies", "user_balances", "transactions"]
            for table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                logger.info(f"✅ {table}: {count} records")
            
            # Test a basic query
            cursor.execute("""
                SELECT u.username, ub.currency_code, ub.total_balance
                FROM users u
                JOIN user_balances ub ON u.id = ub.user_id
                LIMIT 5
            """)
            
            results = cursor.fetchall()
            logger.info(f"✅ Test query returned {len(results)} results")
            
            cursor.close()
            logger.info("✅ Migration verification completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Migration verification failed: {e}")
            return False
    
    def run_migration(self, postgres_password: str) -> bool:
        """Run the complete migration process"""
        logger.info("🚀 Starting PostgreSQL migration...")
        
        try:
            # Step 1: Connect to databases
            if not self.setup_postgres_connection(postgres_password):
                return False
            
            if not self.connect_sqlite():
                logger.warning("⚠️ No SQLite database found - will create empty PostgreSQL database")
            
            # Step 2: Apply PostgreSQL schema
            if not self.apply_postgres_schema():
                return False
            
            # Step 3: Migrate data if SQLite exists
            if self.sqlite_conn:
                if not self.migrate_all_data():
                    return False
            
            # Step 4: Update environment configuration
            if not self.update_environment_config(postgres_password):
                return False
            
            # Step 5: Verify migration
            if not self.verify_migration():
                return False
            
            logger.info("🎉 PostgreSQL migration completed successfully!")
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
    print("🚀 FastAPI Balance Tracking System - PostgreSQL Migration")
    print("=" * 60)
    
    # Get PostgreSQL password
    postgres_password = os.getenv('POSTGRES_PASSWORD')
    if not postgres_password:
        postgres_password = input("Enter PostgreSQL password: ")
        if not postgres_password:
            print("❌ PostgreSQL password is required")
            sys.exit(1)
    
    # Run migration
    migrator = PostgreSQLMigrator()
    
    if migrator.run_migration(postgres_password):
        print("\n🎉 Migration completed successfully!")
        print("\nNext steps:")
        print("1. Install PostgreSQL dependencies: pip install psycopg2-binary")
        print("2. Update your application configuration if needed")
        print("3. Test your application with the new PostgreSQL database")
        print("4. Consider setting up connection pooling for production")
    else:
        print("\n❌ Migration failed! Check the logs above for details.")
        sys.exit(1)


if __name__ == "__main__":
    main()
