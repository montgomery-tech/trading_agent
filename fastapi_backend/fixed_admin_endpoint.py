from fastapi import APIRouter, HTTPException, Depends
from api.dependencies import get_database
from api.database import DatabaseManager
import uuid
import bcrypt
from datetime import datetime

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])

@router.post("/users-fixed")
async def create_user_fixed(
    user_data: dict,
    db: DatabaseManager = Depends(get_database)
):
    """Fixed user creation with explicit commit"""
    
    try:
        email = user_data.get("email")
        full_name = user_data.get("full_name", "Test User")
        role = user_data.get("role", "trader")
        
        if not email:
            raise HTTPException(status_code=400, detail="Email required")
        
        # Generate user data
        user_id = str(uuid.uuid4())
        username = email.split('@')[0] + str(int(datetime.now().timestamp()))
        temp_password = "TempPass123!"
        password_hash = bcrypt.hashpw(temp_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        with db.get_cursor() as cursor:
            # Check if user exists
            cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
            if cursor.fetchone():
                raise HTTPException(status_code=400, detail="User already exists")
            
            # Insert user
            cursor.execute("""
                INSERT INTO users (
                    id, username, email, password_hash, first_name, last_name,
                    is_active, is_verified, must_change_password, created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                user_id, username, email, password_hash, 
                full_name.split()[0] if full_name else "Test",
                " ".join(full_name.split()[1:]) if len(full_name.split()) > 1 else "User",
                True, True, True, datetime.utcnow(), datetime.utcnow()
            ))
            
            # CRITICAL: Explicit commit
            db.connection.commit()
            
            # Verify the insert worked
            cursor.execute("SELECT username FROM users WHERE id = %s", (user_id,))
            if not cursor.fetchone():
                raise Exception("Insert verification failed")
        
        return {
            "success": True,
            "message": "User created with explicit commit",
            "user_id": user_id,
            "username": username,
            "email": email,
            "temporary_password": temp_password,
            "must_change_password": True
        }
        
    except Exception as e:
        # Rollback on error
        try:
            db.connection.rollback()
        except:
            pass
        raise HTTPException(status_code=500, detail=f"User creation failed: {str(e)}")

