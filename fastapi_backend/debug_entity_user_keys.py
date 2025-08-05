#!/usr/bin/env python3
"""
Debug Entity User API Keys
Checks what users exist, their entity assignments, and their API keys
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from api.database import DatabaseManager

def debug_users_entities_keys():
    """Debug the complete user -> entity -> API key chain"""
    
    print("🔍 Entity User API Key Debug")
    print("=" * 50)
    
    # Connect to database
    database_url = os.getenv('DATABASE_URL', 'postgresql://localhost:5432/balance_tracker')
    db = DatabaseManager(database_url)
    db.connect()
    print("✅ Database connected")
    
    # Step 1: Check all users and their entity memberships
    print("\n📋 Step 1: Users and Entity Memberships")
    print("-" * 50)
    
    users_entities = db.execute_query("""
        SELECT 
            u.id,
            u.username, 
            u.email,
            u.is_active as user_active,
            e.id as entity_id,
            e.name as entity_name,
            e.code as entity_code,
            em.entity_role,
            em.is_active as membership_active
        FROM users u
        LEFT JOIN entity_memberships em ON u.id = em.user_id
        LEFT JOIN entities e ON em.entity_id = e.id
        WHERE u.username LIKE '%api_%' OR u.username = 'garrett_admin'
        ORDER BY u.username, e.name
    """)
    
    print(f"Found {len(users_entities)} user-entity relationships:")
    
    current_user = None
    for row in users_entities:
        if row['username'] != current_user:
            current_user = row['username']
            print(f"\n👤 {row['username']} (ID: {row['id']}, Active: {row['user_active']})")
            
        if row['entity_name']:
            print(f"   🏢 Entity: {row['entity_name']} ({row['entity_code']}) - Role: {row['entity_role']} (Active: {row['membership_active']})")
        else:
            print(f"   ❌ No entity membership")
    
    # Step 2: Check API keys for these users
    print("\n📋 Step 2: API Keys for Users")
    print("-" * 40)
    
    api_keys = db.execute_query("""
        SELECT 
            ak.key_id,
            ak.name,
            ak.is_active as key_active,
            ak.permissions_scope,
            u.username,
            u.is_active as user_active
        FROM api_keys ak
        JOIN users u ON ak.user_id = u.id
        WHERE u.username LIKE '%api_%' OR u.username = 'garrett_admin'
        ORDER BY u.username, ak.created_at DESC
    """)
    
    print(f"Found {len(api_keys)} API keys:")
    
    user_key_count = {}
    for key in api_keys:
        username = key['username']
        if username not in user_key_count:
            user_key_count[username] = 0
        user_key_count[username] += 1
        
        print(f"  🔑 {key['key_id']} | {key['name']} | User: {username} | Active: {key['key_active']} | Scope: {key['permissions_scope']}")
    
    print(f"\n📊 API Key Summary:")
    for username, count in user_key_count.items():
        print(f"  - {username}: {count} keys")
    
    # Step 3: Check what happens when we try to authenticate one of the admin keys
    print("\n📋 Step 3: Test Admin Key Authentication")
    print("-" * 50)
    
    admin_keys = [k for k in api_keys if k['username'] == 'garrett_admin']
    if admin_keys:
        admin_key_id = admin_keys[0]['key_id']
        print(f"Testing with admin key: {admin_key_id}")
        
        # Check admin user's entity membership
        admin_entity = db.execute_query("""
            SELECT 
                e.name as entity_name,
                e.code as entity_code,
                em.entity_role
            FROM users u
            LEFT JOIN entity_memberships em ON u.id = em.user_id
            LEFT JOIN entities e ON em.entity_id = e.id
            WHERE u.username = 'garrett_admin'
        """)
        
        if admin_entity and admin_entity[0]['entity_name']:
            print(f"Admin is in entity: {admin_entity[0]['entity_name']} ({admin_entity[0]['entity_code']}) as {admin_entity[0]['entity_role']}")
        else:
            print("❌ Admin has no entity membership!")
    
    # Step 4: Check recent test entities
    print("\n📋 Step 4: Recent Test Entities")
    print("-" * 40)
    
    recent_entities = db.execute_query("""
        SELECT 
            e.name,
            e.code,
            e.created_at,
            COUNT(em.user_id) as member_count
        FROM entities e
        LEFT JOIN entity_memberships em ON e.id = em.entity_id
        WHERE e.code LIKE 'API_%'
        GROUP BY e.id, e.name, e.code, e.created_at
        ORDER BY e.created_at DESC
        LIMIT 10
    """)
    
    print(f"Found {len(recent_entities)} recent test entities:")
    for entity in recent_entities:
        print(f"  🏢 {entity['name']} ({entity['code']}) - {entity['member_count']} members - Created: {entity['created_at']}")
    
    db.disconnect()
    
    # Step 5: Analyze the issue
    print("\n🎯 Issue Analysis")
    print("-" * 30)
    
    test_users = [row for row in users_entities if row['username'].startswith('api_')]
    admin_users = [row for row in users_entities if row['username'] == 'garrett_admin']
    
    if not test_users:
        print("❌ ISSUE: No test users found in database!")
        print("   The test users were likely cleaned up after the test.")
    
    if admin_users and not admin_users[0]['entity_name']:
        print("❌ ISSUE: Admin user has no entity membership!")
        print("   Admin might not be able to access entity-scoped endpoints.")
    
    test_user_keys = [k for k in api_keys if k['username'].startswith('api_')]
    admin_keys = [k for k in api_keys if k['username'] == 'garrett_admin']
    
    print(f"📊 Key distribution:")
    print(f"  - Test users: {len(test_user_keys)} keys")
    print(f"  - Admin user: {len(admin_keys)} keys")
    
    if len(admin_keys) > 5:
        print("⚠️  WARNING: Many admin keys exist (possibly from repeated tests)")


if __name__ == "__main__":
    debug_users_entities_keys()
