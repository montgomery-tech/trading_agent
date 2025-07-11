#!/usr/bin/env python3
"""
Enhanced Database Manager for FastAPI Balance Tracking System
Supports both SQLite (development) and PostgreSQL (production)
Task 1.1: Database Migration to PostgreSQL
"""

import sqlite3
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List, Union
from contextlib import contextmanager
from decimal import Decimal
from datetime import datetime
import os
import sys

# PostgreSQL imports (optional for graceful fallback)
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    from psycopg2.pool import SimpleConnectionPool
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Enhanced database connection and operation manager supporting SQLite and PostgreSQL"""

    def __init__(self, database_url: str = "balance_tracker.db"):
        self.database_url = database_url
        self.connection = None
        self.connection_pool = None
        self.db_type = self._detect_database_type()

        # Connection settings
        self.pool_size = int(os.getenv('DATABASE_POOL_SIZE', '10'))
        self.max_overflow = int(os.getenv('DATABASE_MAX_OVERFLOW', '20'))

        logger.info(f"Database Manager initialized for {self.db_type}")

    def _detect_database_type(self) -> str:
        """Detect database type from URL"""
        if self.database_url.startswith('postgresql://') or self.database_url.startswith('postgres://'):
            return 'postgresql'
        elif self.database_url.startswith('sqlite://'):
            return 'sqlite'
        elif '://' not in self.database_url:
            # Assume SQLite if no protocol specified
            return 'sqlite'
        else:
            raise ValueError(f"Unsupported database URL: {self.database_url}")

    def connect(self):
        """Establish database connection based on database type"""
        if self.db_type == 'postgresql':
            self._connect_postgresql()
        else:
            self._connect_sqlite()

    def _connect_sqlite(self):
        """Establish SQLite connection"""
        try:
            # Handle both file path and sqlite:/// URL format
            if self.database_url.startswith("sqlite:///"):
                db_path = self.database_url.replace("sqlite:///", "")
            else:
                db_path = self.database_url

            if not Path(db_path).exists():
                raise FileNotFoundError(f"Database file not found: {db_path}")

            self.connection = sqlite3.connect(db_path, check_same_thread=False)
            self.connection.row_factory = sqlite3.Row
            self.connection.execute("PRAGMA foreign_keys = ON")

            logger.info(f"✅ Connected to SQLite database: {db_path}")

        except Exception as e:
            logger.error(f"❌ Failed to connect to SQLite database: {e}")
            raise

    def _connect_postgresql(self):
        """Establish PostgreSQL connection with connection pooling"""
        if not POSTGRES_AVAILABLE:
            raise ImportError(
                "PostgreSQL support requires psycopg2. Install with: pip install psycopg2-binary"
            )

        try:
            # Parse connection parameters from URL
            connection_params = self._parse_postgres_url()

            # Test single connection first
            test_conn = psycopg2.connect(**connection_params)
            test_conn.close()

            # Create connection pool for production use
            self.connection_pool = SimpleConnectionPool(
                1,  # min connections
                self.pool_size,  # max connections
                **connection_params
            )

            # Get a connection for immediate use
            self.connection = self.connection_pool.getconn()

            logger.info(f"✅ Connected to PostgreSQL database with connection pool (size: {self.pool_size})")

        except Exception as e:
            logger.error(f"❌ Failed to connect to PostgreSQL database: {e}")
            raise

    def _parse_postgres_url(self) -> Dict[str, Any]:
        """Parse PostgreSQL URL into connection parameters"""
        from urllib.parse import urlparse

        parsed = urlparse(self.database_url)

        if not parsed.hostname:
            raise ValueError(f"Invalid PostgreSQL URL: {self.database_url}")

        params = {
            'host': parsed.hostname,
            'port': parsed.port or 5432,
            'database': parsed.path.lstrip('/'),
            'user': parsed.username,
            'password': parsed.password,
            'cursor_factory': RealDictCursor,  # Returns dict-like rows
        }

        # Add SSL mode if specified in environment
        ssl_mode = os.getenv('DATABASE_SSL_MODE', 'prefer')
        if ssl_mode:
            params['sslmode'] = ssl_mode

        return params

    def disconnect(self):
        """Close database connection"""
        try:
            if self.db_type == 'postgresql' and self.connection_pool:
                if self.connection:
                    self.connection_pool.putconn(self.connection)
                    self.connection = None
                self.connection_pool.closeall()
                self.connection_pool = None
                logger.info("PostgreSQL connection pool closed")

            elif self.connection:
                self.connection.close()
                self.connection = None
                logger.info("Database connection closed")

        except Exception as e:
            logger.warning(f"Error closing database connection: {e}")

    def test_connection(self):
        """Test database connection"""
        if not self.connection:
            raise Exception("No database connection")

        try:
            if self.db_type == 'postgresql':
                cursor = self.connection.cursor()
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                cursor.close()
            else:
                cursor = self.connection.cursor()
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                cursor.close()

            if not result:
                raise Exception("Database connection test failed")

            return True

        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            raise

    @contextmanager
    def get_cursor(self):
        """Get database cursor with automatic cleanup"""
        if self.db_type == 'postgresql':
            cursor = self.connection.cursor()
        else:
            cursor = self.connection.cursor()

        try:
            yield cursor
        finally:
            cursor.close()

    def execute_query(self, query: str, params: tuple = None) -> List[Dict]:
        """Execute a SELECT query and return results"""
        with self.get_cursor() as cursor:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)

            results = []
            for row in cursor.fetchall():
                if self.db_type == 'postgresql':
                    # psycopg2 with RealDictCursor returns dict-like objects
                    results.append(dict(row))
                else:
                    # SQLite with row_factory
                    results.append(dict(row))

            return results

    def execute_command(self, command: str, params: tuple = None) -> int:
        """Execute an INSERT/UPDATE/DELETE command"""
        with self.get_cursor() as cursor:
            if params:
                cursor.execute(command, params)
            else:
                cursor.execute(command)

            self.connection.commit()
            return cursor.rowcount

    def execute_transaction(self, commands: List[tuple]) -> bool:
        """Execute multiple commands in a transaction"""
        try:
            with self.get_cursor() as cursor:
                for command, params in commands:
                    if params:
                        cursor.execute(command, params)
                    else:
                        cursor.execute(command)

                self.connection.commit()
                return True

        except Exception as e:
            self.connection.rollback()
            logger.error(f"Transaction failed: {e}")
            raise

    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        try:
            stats = {
                "database_type": self.db_type,
                "connection_status": "connected" if self.connection else "disconnected",
                "timestamp": datetime.now().isoformat()
            }

            if not self.connection:
                return stats

            with self.get_cursor() as cursor:
                # Get table counts
                if self.db_type == 'postgresql':
                    # PostgreSQL specific queries
                    cursor.execute("""
                        SELECT schemaname, tablename, n_tup_ins, n_tup_upd, n_tup_del
                        FROM pg_stat_user_tables
                        WHERE schemaname = 'public'
                    """)
                    table_stats = cursor.fetchall()

                    cursor.execute("SELECT COUNT(*) FROM users WHERE is_active = true")
                    active_users = cursor.fetchone()[0]

                    cursor.execute("SELECT COUNT(*) FROM user_balances WHERE total_balance > 0")
                    balance_records = cursor.fetchone()[0]

                    cursor.execute("SELECT COUNT(*) FROM transactions")
                    transaction_count = cursor.fetchone()[0]

                    cursor.execute("SELECT COUNT(*) FROM currencies WHERE is_active = true")
                    currency_count = cursor.fetchone()[0]

                    # Database size
                    cursor.execute("SELECT pg_size_pretty(pg_database_size(current_database()))")
                    db_size = cursor.fetchone()[0]

                    stats.update({
                        "active_users": active_users,
                        "balance_records": balance_records,
                        "total_transactions": transaction_count,
                        "active_currencies": currency_count,
                        "database_size": db_size,
                        "table_stats": [dict(row) for row in table_stats]
                    })

                else:
                    # SQLite specific queries
                    cursor.execute("SELECT COUNT(*) FROM users WHERE is_active = 1")
                    active_users = cursor.fetchone()[0]

                    cursor.execute("SELECT COUNT(*) FROM user_balances WHERE total_balance > 0")
                    balance_records = cursor.fetchone()[0]

                    cursor.execute("SELECT COUNT(*) FROM transactions")
                    transaction_count = cursor.fetchone()[0]

                    cursor.execute("SELECT COUNT(*) FROM currencies WHERE is_active = 1")
                    currency_count = cursor.fetchone()[0]

                    # Database file size
                    if hasattr(self, 'database_url') and not self.database_url.startswith('sqlite:///'):
                        db_path = self.database_url
                    else:
                        db_path = self.database_url.replace('sqlite:///', '')

                    try:
                        db_size = f"{Path(db_path).stat().st_size / 1024 / 1024:.2f} MB"
                    except:
                        db_size = "Unknown"

                    stats.update({
                        "active_users": active_users,
                        "balance_records": balance_records,
                        "total_transactions": transaction_count,
                        "active_currencies": currency_count,
                        "database_size": db_size,
                        "database_file": str(Path(db_path).resolve())
                    })

            return stats

        except Exception as e:
            logger.error(f"Error getting database stats: {e}")
            return {"error": str(e), "database_type": self.db_type}

    def get_connection_info(self) -> Dict[str, Any]:
        """Get database connection information"""
        info = {
            "database_type": self.db_type,
            "database_url": self.database_url,
            "connected": bool(self.connection),
        }

        if self.db_type == 'postgresql':
            info.update({
                "pool_size": self.pool_size,
                "max_overflow": self.max_overflow,
                "has_pool": bool(self.connection_pool)
            })

        return info

    def health_check(self) -> Dict[str, Any]:
        """Comprehensive health check"""
        health = {
            "status": "unhealthy",
            "checks": {},
            "timestamp": datetime.now().isoformat()
        }

        try:
            # Test connection
            self.test_connection()
            health["checks"]["connection"] = "healthy"

            # Test basic query
            stats = self.get_stats()
            if "error" not in stats:
                health["checks"]["query"] = "healthy"
                health["stats"] = stats
            else:
                health["checks"]["query"] = f"error: {stats['error']}"

            # Overall status
            if all(check == "healthy" for check in health["checks"].values()):
                health["status"] = "healthy"

        except Exception as e:
            health["checks"]["connection"] = f"error: {str(e)}"

        return health


# Utility functions for database operations
def create_database_manager(database_url: str = None) -> DatabaseManager:
    """Factory function to create database manager"""
    if database_url is None:
        database_url = os.getenv('DATABASE_URL', 'sqlite:///balance_tracker.db')

    return DatabaseManager(database_url)


def validate_database_connection(db_manager: DatabaseManager) -> bool:
    """Validate database connection and basic functionality"""
    try:
        db_manager.test_connection()
        health = db_manager.health_check()
        return health["status"] == "healthy"
    except Exception as e:
        logger.error(f"Database validation failed: {e}")
        return False


# Database schema validation queries
def validate_schema(db_manager: DatabaseManager) -> Dict[str, bool]:
    """Validate that all required tables exist"""
    required_tables = ['users', 'currencies', 'user_balances', 'transactions']
    validation_results = {}

    try:
        with db_manager.get_cursor() as cursor:
            for table in required_tables:
                try:
                    if db_manager.db_type == 'postgresql':
                        cursor.execute(f"SELECT 1 FROM {table} LIMIT 1")
                    else:
                        cursor.execute(f"SELECT 1 FROM {table} LIMIT 1")
                    validation_results[table] = True
                except Exception:
                    validation_results[table] = False

        return validation_results

    except Exception as e:
        logger.error(f"Schema validation failed: {e}")
        return {table: False for table in required_tables}


if __name__ == "__main__":
    """Test database manager functionality"""
    import os

    # Test with environment database URL or default
    db_url = os.getenv('DATABASE_URL', 'sqlite:///balance_tracker.db')

    print(f"Testing DatabaseManager with: {db_url}")

    try:
        db = DatabaseManager(db_url)
        db.connect()

        print("✅ Connection successful")

        # Test health check
        health = db.health_check()
        print(f"Health check: {health['status']}")

        # Test schema validation
        schema_valid = validate_schema(db)
        print(f"Schema validation: {schema_valid}")

        # Get stats
        stats = db.get_stats()
        print(f"Database stats: {stats}")

        db.disconnect()
        print("✅ Test completed successfully")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        sys.exit(1)
