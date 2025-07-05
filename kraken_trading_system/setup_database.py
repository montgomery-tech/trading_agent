#!/usr/bin/env python3
"""
Database Setup Script for User Balance Tracking System
Supports PostgreSQL and SQLite
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path
import sqlite3
#import psycopg2
#from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT


class DatabaseSetup:
    def __init__(self):
        self.schema_file = Path("balance_tracking_schema.sql")
        self.test_file = Path("schema_validation_tests.sql")

    def check_schema_file(self):
        """Check if schema file exists"""
        if not self.schema_file.exists():
            print(f"❌ Error: {self.schema_file} not found!")
            print("Please ensure the schema file is in the current directory.")
            sys.exit(1)

    def setup_postgresql(self, host="localhost", port=5432, dbname="balance_tracker",
                        user="postgres", password=None):
        """Setup PostgreSQL database"""
        print("📊 Setting up PostgreSQL database...")

        if not password:
            password = os.getenv("DB_PASSWORD")
            if not password:
                print("❌ Error: Password required for PostgreSQL")
                print("Set DB_PASSWORD environment variable or use --password option")
                sys.exit(1)

        try:
            # Connect to postgres database to create our database
            print("🔍 Testing database connection...")
            conn = psycopg2.connect(
                host=host, port=port, user=user, password=password, database="postgres"
            )
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cursor = conn.cursor()

            # Create database if it doesn't exist
            print(f"🗄️ Creating database '{dbname}' if it doesn't exist...")
            try:
                cursor.execute(f"CREATE DATABASE {dbname}")
                print(f"✅ Database '{dbname}' created")
            except psycopg2.Error as e:
                if "already exists" in str(e):
                    print(f"ℹ️ Database '{dbname}' already exists")
                else:
                    raise

            cursor.close()
            conn.close()

            # Connect to our new database
            conn = psycopg2.connect(
                host=host, port=port, user=user, password=password, database=dbname
            )
            cursor = conn.cursor()

            # Apply schema
            print("📋 Applying database schema...")
            with open(self.schema_file, 'r') as f:
                schema_sql = f.read()

            cursor.execute(schema_sql)
            conn.commit()
            print("✅ Schema applied successfully!")

            # Run tests if available
            if self.test_file.exists():
                print("🧪 Running validation tests...")
                try:
                    with open(self.test_file, 'r') as f:
                        test_sql = f.read()
                    cursor.execute(test_sql)
                    conn.commit()
                    print("✅ All tests passed!")
                except Exception as e:
                    print(f"⚠️ Some tests failed: {e}")

            cursor.close()
            conn.close()

            print("🎉 PostgreSQL setup complete!")
            print(f"Connection string: postgresql://{user}:****@{host}:{port}/{dbname}")

        except Exception as e:
            print(f"❌ PostgreSQL setup failed: {e}")
            sys.exit(1)

    def setup_sqlite(self, db_file="balance_tracker.db"):
        """Setup SQLite database"""
        print("📁 Setting up SQLite database...")

        # SQLite-compatible schema (simplified from PostgreSQL)
        sqlite_schema = """
-- SQLite version of the User Balance Tracking System Schema
PRAGMA foreign_keys = ON;

-- Users Table
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    is_active BOOLEAN DEFAULT 1,
    is_verified BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP,
    CHECK (LENGTH(username) >= 3)
);

-- Currencies Table
CREATE TABLE IF NOT EXISTS currencies (
    code VARCHAR(10) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    symbol VARCHAR(10),
    decimal_places INTEGER DEFAULT 8,
    is_active BOOLEAN DEFAULT 1,
    is_fiat BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CHECK (decimal_places >= 0 AND decimal_places <= 18)
);

-- User Balances Table
CREATE TABLE IF NOT EXISTS user_balances (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    currency_code VARCHAR(10) NOT NULL REFERENCES currencies(code),
    total_balance DECIMAL(28, 18) DEFAULT 0 NOT NULL,
    available_balance DECIMAL(28, 18) DEFAULT 0 NOT NULL,
    locked_balance DECIMAL(28, 18) DEFAULT 0 NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, currency_code),
    CHECK (total_balance >= 0),
    CHECK (available_balance >= 0),
    CHECK (locked_balance >= 0),
    CHECK (total_balance = available_balance + locked_balance)
);

-- Transactions Table
CREATE TABLE IF NOT EXISTS transactions (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    user_id TEXT NOT NULL REFERENCES users(id),
    external_id VARCHAR(255),
    transaction_type VARCHAR(20) NOT NULL CHECK (transaction_type IN ('deposit', 'withdrawal', 'trade_buy', 'trade_sell', 'transfer_in', 'transfer_out', 'fee', 'adjustment')),
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed', 'cancelled', 'rejected')),
    amount DECIMAL(28, 18) NOT NULL,
    currency_code VARCHAR(10) NOT NULL REFERENCES currencies(code),
    fee_amount DECIMAL(28, 18) DEFAULT 0,
    fee_currency_code VARCHAR(10) REFERENCES currencies(code),
    balance_before DECIMAL(28, 18),
    balance_after DECIMAL(28, 18),
    description TEXT,
    metadata TEXT,
    related_transaction_id TEXT REFERENCES transactions(id),
    external_reference VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP,
    CHECK (amount > 0),
    CHECK (fee_amount >= 0)
);

-- Trading Pairs Table
CREATE TABLE IF NOT EXISTS trading_pairs (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    base_currency VARCHAR(10) NOT NULL REFERENCES currencies(code),
    quote_currency VARCHAR(10) NOT NULL REFERENCES currencies(code),
    symbol VARCHAR(20) NOT NULL UNIQUE,
    min_trade_amount DECIMAL(28, 18) DEFAULT 0,
    max_trade_amount DECIMAL(28, 18),
    price_precision INTEGER DEFAULT 8,
    amount_precision INTEGER DEFAULT 8,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CHECK (base_currency != quote_currency),
    CHECK (min_trade_amount >= 0)
);

-- Trades Table
CREATE TABLE IF NOT EXISTS trades (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    user_id TEXT NOT NULL REFERENCES users(id),
    trading_pair_id TEXT NOT NULL REFERENCES trading_pairs(id),
    side VARCHAR(4) NOT NULL CHECK (side IN ('buy', 'sell')),
    amount DECIMAL(28, 18) NOT NULL,
    price DECIMAL(28, 18) NOT NULL,
    total_value DECIMAL(28, 18) NOT NULL,
    fee_amount DECIMAL(28, 18) DEFAULT 0,
    fee_currency_code VARCHAR(10) REFERENCES currencies(code),
    status VARCHAR(20) DEFAULT 'pending',
    executed_at TIMESTAMP,
    base_transaction_id TEXT REFERENCES transactions(id),
    quote_transaction_id TEXT REFERENCES transactions(id),
    fee_transaction_id TEXT REFERENCES transactions(id),
    external_trade_id VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CHECK (amount > 0),
    CHECK (price > 0)
);

-- Balance Snapshots Table
CREATE TABLE IF NOT EXISTS balance_snapshots (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    user_id TEXT NOT NULL REFERENCES users(id),
    currency_code VARCHAR(10) NOT NULL REFERENCES currencies(code),
    total_balance DECIMAL(28, 18) NOT NULL,
    available_balance DECIMAL(28, 18) NOT NULL,
    locked_balance DECIMAL(28, 18) NOT NULL,
    snapshot_type VARCHAR(20) DEFAULT 'periodic',
    triggered_by_transaction_id TEXT REFERENCES transactions(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CHECK (total_balance = available_balance + locked_balance)
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_user_balances_user_id ON user_balances(user_id);
CREATE INDEX IF NOT EXISTS idx_user_balances_currency ON user_balances(currency_code);
CREATE INDEX IF NOT EXISTS idx_transactions_user_id ON transactions(user_id);
CREATE INDEX IF NOT EXISTS idx_transactions_type ON transactions(transaction_type);
CREATE INDEX IF NOT EXISTS idx_transactions_status ON transactions(status);
CREATE INDEX IF NOT EXISTS idx_trades_user_id ON trades(user_id);
CREATE INDEX IF NOT EXISTS idx_trades_pair_id ON trades(trading_pair_id);

-- Insert initial data
INSERT OR IGNORE INTO currencies (code, name, symbol, decimal_places, is_fiat) VALUES
('USD', 'US Dollar', '$', 2, 1),
('EUR', 'Euro', '€', 2, 1),
('GBP', 'British Pound', '£', 2, 1),
('BTC', 'Bitcoin', '₿', 8, 0),
('ETH', 'Ethereum', 'Ξ', 8, 0),
('LTC', 'Litecoin', 'Ł', 8, 0),
('ADA', 'Cardano', '₳', 6, 0),
('SOL', 'Solana', 'SOL', 6, 0);

-- Insert trading pairs
INSERT OR IGNORE INTO trading_pairs (base_currency, quote_currency, symbol, min_trade_amount, price_precision, amount_precision) VALUES
('BTC', 'USD', 'BTC/USD', 0.00001, 2, 8),
('ETH', 'USD', 'ETH/USD', 0.001, 2, 8),
('ETH', 'BTC', 'ETH/BTC', 0.001, 8, 8),
('LTC', 'USD', 'LTC/USD', 0.01, 2, 8),
('ADA', 'USD', 'ADA/USD', 1, 4, 6),
('SOL', 'USD', 'SOL/USD', 0.1, 2, 6);
"""

        try:
            # Create SQLite database
            print(f"📋 Creating SQLite database: {db_file}")
            conn = sqlite3.connect(db_file)
            cursor = conn.cursor()

            # Execute schema
            cursor.executescript(sqlite_schema)
            conn.commit()

            print("✅ SQLite database created successfully!")

            # Test basic queries
            print("🧪 Running basic validation...")
            cursor.execute("SELECT COUNT(*) FROM currencies")
            currency_count = cursor.fetchone()[0]
            print(f"✅ {currency_count} currencies loaded")

            cursor.execute("SELECT COUNT(*) FROM trading_pairs")
            pairs_count = cursor.fetchone()[0]
            print(f"✅ {pairs_count} trading pairs loaded")

            cursor.close()
            conn.close()

            print("🎉 SQLite setup complete!")
            print(f"Database file: {db_file}")
            print(f"To connect: sqlite3 {db_file}")

        except Exception as e:
            print(f"❌ SQLite setup failed: {e}")
            sys.exit(1)

    def setup_docker_postgresql(self, dbname="balance_tracker", user="postgres", password="postgres123"):
        """Setup PostgreSQL via Docker"""
        print("🐳 Setting up PostgreSQL via Docker...")

        try:
            # Check if Docker is available
            subprocess.run(["docker", "--version"], check=True, capture_output=True)
        except subprocess.CalledProcessError:
            print("❌ Docker is not installed or not available")
            sys.exit(1)

        container_name = "balance-tracker-db"
        port = 5432

        try:
            # Check if container exists
            result = subprocess.run(
                ["docker", "ps", "-a", "--format", "{{.Names}}"],
                capture_output=True, text=True
            )

            if container_name in result.stdout:
                print("📦 Existing container found. Starting it...")
                subprocess.run(["docker", "start", container_name], check=True)
            else:
                print("📦 Creating new PostgreSQL container...")
                subprocess.run([
                    "docker", "run", "-d",
                    "--name", container_name,
                    "-e", f"POSTGRES_DB={dbname}",
                    "-e", f"POSTGRES_USER={user}",
                    "-e", f"POSTGRES_PASSWORD={password}",
                    "-p", f"{port}:5432",
                    "postgres:15-alpine"
                ], check=True)

            print("⏳ Waiting for database to be ready...")
            import time
            time.sleep(10)

            # Now setup the database using PostgreSQL method
            self.setup_postgresql("localhost", port, dbname, user, password)

            print(f"🎉 Docker PostgreSQL setup complete!")
            print(f"Container: {container_name}")
            print(f"Connection: postgresql://{user}:{password}@localhost:{port}/{dbname}")
            print(f"To stop: docker stop {container_name}")
            print(f"To remove: docker rm {container_name}")

        except subprocess.CalledProcessError as e:
            print(f"❌ Docker setup failed: {e}")
            sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Setup database for User Balance Tracking System")
    parser.add_argument("database_type", choices=["postgresql", "sqlite", "docker-pg"],
                       help="Database type to setup")

    # PostgreSQL options
    parser.add_argument("--host", default="localhost", help="Database host (PostgreSQL)")
    parser.add_argument("--port", type=int, default=5432, help="Database port (PostgreSQL)")
    parser.add_argument("--dbname", default="balance_tracker", help="Database name")
    parser.add_argument("--user", default="postgres", help="Database user (PostgreSQL)")
    parser.add_argument("--password", help="Database password (PostgreSQL)")

    # SQLite options
    parser.add_argument("--db-file", default="balance_tracker.db", help="SQLite database file")

    args = parser.parse_args()

    print("🚀 User Balance Tracking System - Database Setup")
    print("=" * 50)

    setup = DatabaseSetup()

    # Check for schema file only for PostgreSQL (SQLite uses embedded schema)
    if args.database_type == "postgresql":
        setup.check_schema_file()

    if args.database_type == "postgresql":
        setup.setup_postgresql(
            host=args.host,
            port=args.port,
            dbname=args.dbname,
            user=args.user,
            password=args.password
        )
    elif args.database_type == "sqlite":
        setup.setup_sqlite(args.db_file)
    elif args.database_type == "docker-pg":
        setup.setup_docker_postgresql(
            dbname=args.dbname,
            user=args.user,
            password=args.password or "postgres123"
        )

    print("\n🎯 Database setup completed successfully!")
    print("You can now start building your balance tracking application.")


if __name__ == "__main__":
    # Check for required packages
    try:
        import psycopg2
    except ImportError:
        print("⚠️ psycopg2 not found. Install it with: pip install psycopg2-binary")
        print("(Only needed for PostgreSQL)")

    main()
