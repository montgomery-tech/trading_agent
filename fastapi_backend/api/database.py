"""
Database management for the Balance Tracking API
"""

import sqlite3
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from contextlib import contextmanager
from decimal import Decimal

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Database connection and operation manager"""
    
    def __init__(self, database_url: str = "balance_tracker.db"):
        self.database_url = database_url
        self.connection = None
        
    def connect(self):
        """Establish database connection"""
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
            logger.error(f"❌ Failed to connect to database: {e}")
            raise
    
    def disconnect(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            self.connection = None
            logger.info("Database connection closed")
    
    def test_connection(self):
        """Test database connection"""
        if not self.connection:
            raise Exception("No database connection")
        
        cursor = self.connection.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        cursor.close()
        
        if not result:
            raise Exception("Database connection test failed")
        
        return True
    
    @contextmanager
    def get_cursor(self):
        """Get database cursor with automatic cleanup"""
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
                cursor.execute("BEGIN TRANSACTION")
                
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
        stats = {}
        tables = ["users", "currencies", "user_balances", "transactions", "trades"]
        
        for table in tables:
            try:
                result = self.execute_query(f"SELECT COUNT(*) as count FROM {table}")
                stats[table] = result[0]["count"] if result else 0
            except:
                stats[table] = 0
        
        return stats
