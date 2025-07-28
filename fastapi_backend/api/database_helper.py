#!/usr/bin/env python3
"""
Database Helper Utilities
Provides consistent database query handling for PostgreSQL and SQLite
"""

def format_query_for_db(db, query, params=None):
    """
    Format query and parameters for the specific database type
    
    Args:
        db: DatabaseManager instance
        query: SQL query string with ? placeholders
        params: Query parameters tuple
    
    Returns:
        Tuple of (formatted_query, params)
    """
    if db.db_type == 'postgresql':
        # Convert ? to %s for PostgreSQL
        formatted_query = query.replace('?', '%s')
        return formatted_query, params or ()
    else:
        # Keep ? for SQLite
        return query, params or ()

def safe_execute_query(db, query, params=None):
    """
    Safely execute a query with proper error handling
    
    Args:
        db: DatabaseManager instance
        query: SQL query string
        params: Query parameters
    
    Returns:
        Query results or empty list on error
    """
    try:
        formatted_query, formatted_params = format_query_for_db(db, query, params)
        return db.execute_query(formatted_query, formatted_params)
    except Exception as e:
        print(f"Database query error: {e}")
        print(f"Query: {query}")
        print(f"Params: {params}")
        return []

def build_where_clause(conditions, db_type='postgresql'):
    """
    Build a WHERE clause with proper parameter placeholders
    
    Args:
        conditions: List of condition strings
        db_type: Database type ('postgresql' or 'sqlite')
    
    Returns:
        WHERE clause string
    """
    if not conditions:
        return ""
    
    placeholder = '%s' if db_type == 'postgresql' else '?'
    where_clause = "WHERE " + " AND ".join(conditions)
    
    return where_clause
