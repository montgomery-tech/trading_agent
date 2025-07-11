#!/usr/bin/env python3
"""
PostgreSQL Migration Test Script
Task 1.1: Database Migration to PostgreSQL

Tests the migration process and validates the new PostgreSQL setup
"""

import os
import sys
import time
from pathlib import Path
import logging
from typing import Dict, Any, List

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

try:
    from updated_database_manager import DatabaseManager, validate_schema
except ImportError:
    logger.error("Could not import DatabaseManager. Ensure the updated database manager is available.")
    sys.exit(1)


class MigrationTester:
    """Test suite for PostgreSQL migration"""
    
    def __init__(self):
        self.test_results = {}
        self.sqlite_db = None
        self.postgres_db = None
        
    def setup_test_environment(self) -> bool:
        """Setup test environment"""
        logger.info("🧪 Setting up test environment...")
        
        try:
            # Check if SQLite database exists
            sqlite_path = "balance_tracker.db"
            if Path(sqlite_path).exists():
                logger.info(f"✅ Found SQLite database: {sqlite_path}")
                self.sqlite_db = DatabaseManager(f"sqlite:///{sqlite_path}")
            else:
                logger.warning("⚠️ No SQLite database found for comparison")
            
            # Setup PostgreSQL connection
            postgres_url = os.getenv('DATABASE_URL', 'postgresql://postgres:dev_password_123@localhost:5432/balance_tracker')
            logger.info(f"Setting up PostgreSQL connection: {postgres_url}")
            
            self.postgres_db = DatabaseManager(postgres_url)
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to setup test environment: {e}")
            return False
    
    def test_postgres_connection(self) -> bool:
        """Test PostgreSQL connection"""
        logger.info("🔍 Testing PostgreSQL connection...")
        
        try:
            self.postgres_db.connect()
            self.postgres_db.test_connection()
            
            connection_info = self.postgres_db.get_connection_info()
            logger.info(f"✅ PostgreSQL connection successful")
            logger.info(f"   Database type: {connection_info['database_type']}")
            logger.info(f"   Pool size: {connection_info.get('pool_size', 'N/A')}")
            
            self.test_results['postgres_connection'] = True
            return True
            
        except Exception as e:
            logger.error(f"❌ PostgreSQL connection failed: {e}")
            self.test_results['postgres_connection'] = False
            return False
    
    def test_schema_validation(self) -> bool:
        """Test that all required tables exist in PostgreSQL"""
        logger.info("📋 Testing schema validation...")
        
        try:
            schema_results = validate_schema(self.postgres_db)
            
            all_valid = all(schema_results.values())
            if all_valid:
                logger.info("✅ All required tables exist")
                for table, exists in schema_results.items():
                    logger.info(f"   {table}: {'✅' if exists else '❌'}")
            else:
                logger.error("❌ Schema validation failed")
                for table, exists in schema_results.items():
                    logger.info(f"   {table}: {'✅' if exists else '❌'}")
            
            self.test_results['schema_validation'] = all_valid
            return all_valid
            
        except Exception as e:
            logger.error(f"❌ Schema validation error: {e}")
            self.test_results['schema_validation'] = False
            return False
    
    def test_data_integrity(self) -> bool:
        """Test data integrity and basic queries"""
        logger.info("🔍 Testing data integrity...")
        
        try:
            # Test basic counts
            with self.postgres_db.get_cursor() as cursor:
                # Test currencies
                cursor.execute("SELECT COUNT(*) FROM currencies")
                currency_count = cursor.fetchone()[0]
                logger.info(f"   Currencies: {currency_count} records")
                
                # Test users
                cursor.execute("SELECT COUNT(*) FROM users")
                user_count = cursor.fetchone()[0]
                logger.info(f"   Users: {user_count} records")
                
                # Test balances
                cursor.execute("SELECT COUNT(*) FROM user_balances")
                balance_count = cursor.fetchone()[0]
                logger.info(f"   Balances: {balance_count} records")
                
                # Test transactions
                cursor.execute("SELECT COUNT(*) FROM transactions")
                transaction_count = cursor.fetchone()[0]
                logger.info(f"   Transactions: {transaction_count} records")
                
                # Test relationships
                cursor.execute("""
                    SELECT u.username, ub.currency_code, ub.total_balance
                    FROM users u
                    JOIN user_balances ub ON u.id = ub.user_id
                    LIMIT 5
                """)
                sample_data = cursor.fetchall()
                logger.info(f"   Sample joined data: {len(sample_data)} records")
            
            self.test_results['data_integrity'] = True
            return True
            
        except Exception as e:
            logger.error(f"❌ Data integrity test failed: {e}")
            self.test_results['data_integrity'] = False
            return False
    
    def test_postgresql_features(self) -> bool:
        """Test PostgreSQL-specific features"""
        logger.info("🚀 Testing PostgreSQL features...")
        
        try:
            with self.postgres_db.get_cursor() as cursor:
                # Test UUID generation
                cursor.execute("SELECT uuid_generate_v4()")
                uuid_result = cursor.fetchone()[0]
                logger.info(f"   UUID generation: {uuid_result}")
                
                # Test JSON support
                cursor.execute("SELECT '{\"test\": \"data\"}'::jsonb")
                json_result = cursor.fetchone()[0]
                logger.info(f"   JSONB support: {json_result}")
                
                # Test timestamp with timezone
                cursor.execute("SELECT CURRENT_TIMESTAMP")
                timestamp_result = cursor.fetchone()[0]
                logger.info(f"   Timestamp: {timestamp_result}")
                
                # Test database size
                cursor.execute("SELECT pg_size_pretty(pg_database_size(current_database()))")
                db_size = cursor.fetchone()[0]
                logger.info(f"   Database size: {db_size}")
            
            self.test_results['postgresql_features'] = True
            return True
            
        except Exception as e:
            logger.error(f"❌ PostgreSQL features test failed: {e}")
            self.test_results['postgresql_features'] = False
            return False
    
    def test_performance_basic(self) -> bool:
        """Test basic performance metrics"""
        logger.info("⚡ Testing basic performance...")
        
        try:
            # Test query performance
            start_time = time.time()
            
            with self.postgres_db.get_cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        u.username,
                        COUNT(ub.id) as balance_count,
                        COUNT(t.id) as transaction_count
                    FROM users u
                    LEFT JOIN user_balances ub ON u.id = ub.user_id
                    LEFT JOIN transactions t ON u.id = t.user_id
                    GROUP BY u.id, u.username
                    LIMIT 10
                """)
                results = cursor.fetchall()
            
            query_time = time.time() - start_time
            logger.info(f"   Complex query time: {query_time:.3f}s")
            logger.info(f"   Results returned: {len(results)}")
            
            # Test insert performance
            start_time = time.time()
            
            test_user_id = None
            with self.postgres_db.get_cursor() as cursor:
                cursor.execute("""
                    INSERT INTO users (username, email, password_hash, first_name, last_name)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id
                """, ('test_user_migration', 'test@migration.com', 'hash123', 'Test', 'User'))
                
                test_user_id = cursor.fetchone()[0]
                self.postgres_db.connection.commit()
            
            insert_time = time.time() - start_time
            logger.info(f"   Insert time: {insert_time:.3f}s")
            
            # Cleanup test user
            if test_user_id:
                with self.postgres_db.get_cursor() as cursor:
                    cursor.execute("DELETE FROM users WHERE id = %s", (test_user_id,))
                    self.postgres_db.connection.commit()
            
            # Performance is acceptable if queries complete in reasonable time
            performance_ok = query_time < 1.0 and insert_time < 1.0
            
            self.test_results['performance_basic'] = performance_ok
            return performance_ok
            
        except Exception as e:
            logger.error(f"❌ Performance test failed: {e}")
            self.test_results['performance_basic'] = False
            return False
    
    def compare_with_sqlite(self) -> bool:
        """Compare data between SQLite and PostgreSQL if both available"""
        if not self.sqlite_db:
            logger.info("⚠️ Skipping SQLite comparison - no SQLite database found")
            self.test_results['sqlite_comparison'] = True
            return True
        
        logger.info("🔍 Comparing SQLite and PostgreSQL data...")
        
        try:
            self.sqlite_db.connect()
            
            # Compare record counts
            tables = ['users', 'currencies', 'user_balances', 'transactions']
            comparison_results = {}
            
            for table in tables:
                # SQLite count
                sqlite_count = self.sqlite_db.execute_query(f"SELECT COUNT(*) as count FROM {table}")[0]['count']
                
                # PostgreSQL count
                postgres_count = self.postgres_db.execute_query(f"SELECT COUNT(*) as count FROM {table}")[0]['count']
                
                comparison_results[table] = {
                    'sqlite': sqlite_count,
                    'postgres': postgres_count,
                    'match': sqlite_count == postgres_count
                }
                
                logger.info(f"   {table}: SQLite={sqlite_count}, PostgreSQL={postgres_count}, Match={'✅' if sqlite_count == postgres_count else '❌'}")
            
            # Overall comparison result
            all_match = all(result['match'] for result in comparison_results.values())
            
            self.test_results['sqlite_comparison'] = all_match
            return all_match
            
        except Exception as e:
            logger.error(f"❌ SQLite comparison failed: {e}")
            self.test_results['sqlite_comparison'] = False
            return False
        
        finally:
            if self.sqlite_db:
                self.sqlite_db.disconnect()
    
    def test_health_check(self) -> bool:
        """Test database health check functionality"""
        logger.info("🏥 Testing health check functionality...")
        
        try:
            health = self.postgres_db.health_check()
            
            logger.info(f"   Health status: {health['status']}")
            for check, result in health['checks'].items():
                logger.info(f"   {check}: {result}")
            
            if 'stats' in health:
                stats = health['stats']
                logger.info(f"   Active users: {stats.get('active_users', 'N/A')}")
                logger.info(f"   Database size: {stats.get('database_size', 'N/A')}")
            
            health_ok = health['status'] == 'healthy'
            self.test_results['health_check'] = health_ok
            return health_ok
            
        except Exception as e:
            logger.error(f"❌ Health check test failed: {e}")
            self.test_results['health_check'] = False
            return False
    
    def run_all_tests(self) -> bool:
        """Run all migration tests"""
        logger.info("🧪 Starting PostgreSQL Migration Test Suite")
        logger.info("=" * 50)
        
        # Setup
        if not self.setup_test_environment():
            return False
        
        # Run tests
        tests = [
            ('PostgreSQL Connection', self.test_postgres_connection),
            ('Schema Validation', self.test_schema_validation),
            ('Data Integrity', self.test_data_integrity),
            ('PostgreSQL Features', self.test_postgresql_features),
            ('Basic Performance', self.test_performance_basic),
            ('SQLite Comparison', self.compare_with_sqlite),
            ('Health Check', self.test_health_check),
        ]
        
        passed_tests = 0
        total_tests = len(tests)
        
        for test_name, test_func in tests:
            logger.info(f"\n🔍 Running: {test_name}")
            try:
                if test_func():
                    logger.info(f"✅ {test_name}: PASSED")
                    passed_tests += 1
                else:
                    logger.error(f"❌ {test_name}: FAILED")
            except Exception as e:
                logger.error(f"❌ {test_name}: ERROR - {e}")
        
        # Summary
        logger.info("\n" + "=" * 50)
        logger.info("🧪 TEST SUMMARY")
        logger.info("=" * 50)
        
        for test_name, result in self.test_results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            logger.info(f"   {test_name}: {status}")
        
        logger.info(f"\nOverall: {passed_tests}/{total_tests} tests passed")
        
        if passed_tests == total_tests:
            logger.info("🎉 All tests passed! Migration is successful.")
            return True
        else:
            logger.error(f"❌ {total_tests - passed_tests} tests failed. Review the errors above.")
            return False
    
    def cleanup(self):
        """Cleanup test connections"""
        try:
            if self.postgres_db:
                self.postgres_db.disconnect()
            if self.sqlite_db:
                self.sqlite_db.disconnect()
        except Exception as e:
            logger.warning(f"Cleanup warning: {e}")


def run_quick_connectivity_test():
    """Quick test to verify PostgreSQL is accessible"""
    logger.info("🔍 Quick connectivity test...")
    
    try:
        postgres_url = os.getenv('DATABASE_URL', 'postgresql://postgres:dev_password_123@localhost:5432/balance_tracker')
        db = DatabaseManager(postgres_url)
        db.connect()
        db.test_connection()
        db.disconnect()
        
        logger.info("✅ Quick connectivity test passed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Quick connectivity test failed: {e}")
        logger.error("Ensure PostgreSQL is running and accessible")
        return False


def main():
    """Main test execution"""
    print("🐘 PostgreSQL Migration Test Suite")
    print("=" * 40)
    
    # Check if this is a quick test or full test
    if len(sys.argv) > 1 and sys.argv[1] == "quick":
        return run_quick_connectivity_test()
    
    # Run full test suite
    tester = MigrationTester()
    
    try:
        success = tester.run_all_tests()
        
        if success:
            print("\n🎉 Migration test completed successfully!")
            print("\nYour PostgreSQL migration is ready for production!")
            print("\nNext steps:")
            print("1. Update your FastAPI application configuration")
            print("2. Run your application with PostgreSQL")
            print("3. Monitor performance and optimize as needed")
            
            return True
        else:
            print("\n❌ Migration test failed!")
            print("\nReview the errors above and fix issues before proceeding.")
            return False
            
    except KeyboardInterrupt:
        print("\n⚠️ Test interrupted by user")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error during testing: {e}")
        return False
    finally:
        tester.cleanup()


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
