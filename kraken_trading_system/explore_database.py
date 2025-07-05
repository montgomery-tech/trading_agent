#!/usr/bin/env python3
"""
Simple Database Explorer Script
Helps you understand the structure and content of your balance tracking database
No external dependencies required!
"""

import sqlite3
import sys
from pathlib import Path


class SimpleDatabaseExplorer:
    def __init__(self, db_file="balance_tracker.db"):
        self.db_file = db_file
        self.conn = None

    def connect(self):
        """Connect to the database"""
        if not Path(self.db_file).exists():
            print(f"❌ Database file '{self.db_file}' not found!")
            print("Make sure you've run the setup script first.")
            sys.exit(1)

        self.conn = sqlite3.connect(self.db_file)
        self.conn.row_factory = sqlite3.Row
        print(f"✅ Connected to database: {self.db_file}")

    def disconnect(self):
        """Disconnect from database"""
        if self.conn:
            self.conn.close()

    def get_all_tables(self):
        """Get list of all tables in the database"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table'
            ORDER BY name
        """)
        return [row[0] for row in cursor.fetchall()]

    def get_table_schema(self, table_name):
        """Get the schema (column information) for a table"""
        cursor = self.conn.cursor()
        cursor.execute(f"PRAGMA table_info({table_name})")
        return cursor.fetchall()

    def get_table_data(self, table_name, limit=5):
        """Get sample data from a table"""
        cursor = self.conn.cursor()
        cursor.execute(f"SELECT * FROM {table_name} LIMIT {limit}")
        return cursor.fetchall()

    def get_table_count(self, table_name):
        """Get total number of rows in a table"""
        cursor = self.conn.cursor()
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        return cursor.fetchone()[0]

    def print_separator(self, char="=", length=60):
        """Print a separator line"""
        print(char * length)

    def show_table_info(self, table_name):
        """Show comprehensive information about a table"""
        print(f"\n🗂️  TABLE: {table_name.upper()}")
        self.print_separator()

        # Get row count
        count = self.get_table_count(table_name)
        print(f"📊 Total rows: {count}")

        # Get schema
        schema = self.get_table_schema(table_name)
        print(f"\n📋 Schema:")
        print(f"{'Column':<20} {'Type':<15} {'Null?':<8} {'Default':<15} {'PK?':<5}")
        print("-" * 70)

        for col in schema:
            col_name = col[1]
            col_type = col[2]
            not_null = "NO" if col[3] else "YES"
            default = str(col[4]) if col[4] is not None else ""
            is_pk = "YES" if col[5] else "NO"

            print(f"{col_name:<20} {col_type:<15} {not_null:<8} {default:<15} {is_pk:<5}")

        # Show sample data if table has data
        if count > 0:
            print(f"\n📄 Sample data (showing up to 5 rows):")
            data = self.get_table_data(table_name, 5)

            if data:
                # Get column names
                columns = [col[1] for col in schema]

                # Print header
                header = " | ".join(f"{col[:15]:<15}" for col in columns)
                print(header)
                print("-" * len(header))

                # Print data rows
                for row in data:
                    row_data = []
                    for i, value in enumerate(row):
                        if value is None:
                            row_data.append("NULL")
                        else:
                            str_val = str(value)
                            # Truncate long values
                            if len(str_val) > 15:
                                str_val = str_val[:12] + "..."
                            row_data.append(str_val)

                    row_str = " | ".join(f"{val:<15}" for val in row_data)
                    print(row_str)
            else:
                print("No data in this table")
        else:
            print("\n📄 Table is empty")

    def show_database_overview(self):
        """Show overview of entire database"""
        print("\n🎯 DATABASE OVERVIEW")
        self.print_separator()

        tables = self.get_all_tables()

        print(f"{'Table Name':<20} {'Rows':<10} {'Columns':<10}")
        print("-" * 45)

        total_rows = 0
        for table in tables:
            count = self.get_table_count(table)
            schema = self.get_table_schema(table)
            col_count = len(schema)
            total_rows += count

            print(f"{table:<20} {count:<10} {col_count:<10}")

        print("-" * 45)
        print(f"{'TOTAL':<20} {total_rows:<10} {len(tables)} tables")

    def show_relationships(self):
        """Show foreign key relationships between tables"""
        print("\n🔗 TABLE RELATIONSHIPS")
        self.print_separator()

        tables = self.get_all_tables()
        relationships = []

        for table in tables:
            cursor = self.conn.cursor()
            cursor.execute(f"PRAGMA foreign_key_list({table})")
            fks = cursor.fetchall()

            for fk in fks:
                relationships.append({
                    'from_table': table,
                    'from_column': fk[3],
                    'to_table': fk[2],
                    'to_column': fk[4]
                })

        if relationships:
            print(f"{'From Table':<15} {'From Column':<15} {'To Table':<15} {'To Column':<15}")
            print("-" * 65)
            for rel in relationships:
                print(f"{rel['from_table']:<15} {rel['from_column']:<15} {rel['to_table']:<15} {rel['to_column']:<15}")
        else:
            print("No foreign key relationships found")

    def show_sample_queries(self):
        """Show some useful sample queries"""
        print("\n🔍 USEFUL SAMPLE QUERIES")
        self.print_separator()

        queries = [
            {
                "description": "All available currencies",
                "sql": "SELECT code, name, symbol, is_fiat FROM currencies WHERE is_active = 1"
            },
            {
                "description": "All trading pairs",
                "sql": "SELECT symbol, base_currency, quote_currency, is_active FROM trading_pairs"
            },
            {
                "description": "User count",
                "sql": "SELECT COUNT(*) as total_users FROM users"
            }
        ]

        for i, query in enumerate(queries, 1):
            print(f"\n{i}. {query['description']}:")
            print(f"   SQL: {query['sql']}")

            try:
                cursor = self.conn.cursor()
                cursor.execute(query['sql'])
                results = cursor.fetchall()

                if results:
                    print(f"   Results:")
                    # Get column names
                    columns = [desc[0] for desc in cursor.description]
                    header = " | ".join(f"{col:<12}" for col in columns)
                    print(f"   {header}")
                    print(f"   {'-' * len(header)}")

                    for row in results:
                        row_data = []
                        for value in row:
                            if value is None:
                                row_data.append("NULL")
                            else:
                                str_val = str(value)
                                if len(str_val) > 12:
                                    str_val = str_val[:9] + "..."
                                row_data.append(str_val)
                        row_str = " | ".join(f"{val:<12}" for val in row_data)
                        print(f"   {row_str}")
                else:
                    print("   No results")
            except Exception as e:
                print(f"   Error: {e}")

    def explore_all(self):
        """Run complete database exploration"""
        self.connect()

        print("🚀 BALANCE TRACKING DATABASE EXPLORER")
        self.print_separator("=", 80)

        # Show overview
        self.show_database_overview()

        # Show relationships
        self.show_relationships()

        # Show each table in detail
        tables = self.get_all_tables()
        for table in tables:
            self.show_table_info(table)

        # Show sample queries
        self.show_sample_queries()

        print("\n" + "=" * 80)
        print("🎯 Database exploration complete!")
        print("💡 You can now connect to your database and start building your application.")

        self.disconnect()


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Explore the balance tracking database")
    parser.add_argument("--db-file", default="balance_tracker.db",
                       help="Database file path (default: balance_tracker.db)")
    parser.add_argument("--table", help="Show details for specific table only")
    parser.add_argument("--overview", action="store_true",
                       help="Show only database overview")

    args = parser.parse_args()

    explorer = SimpleDatabaseExplorer(args.db_file)

    try:
        if args.overview:
            explorer.connect()
            explorer.show_database_overview()
            explorer.disconnect()
        elif args.table:
            explorer.connect()
            if args.table in explorer.get_all_tables():
                explorer.show_table_info(args.table)
            else:
                print(f"❌ Table '{args.table}' not found!")
                print("Available tables:", ", ".join(explorer.get_all_tables()))
            explorer.disconnect()
        else:
            explorer.explore_all()

    except KeyboardInterrupt:
        print("\n\n👋 Exploration cancelled by user")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        if explorer.conn:
            explorer.disconnect()


if __name__ == "__main__":
    main()
