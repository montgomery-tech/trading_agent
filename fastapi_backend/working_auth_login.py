from fastapi import APIRouter, HTTPException, Depends
from api.dependencies import get_database
from api.database import DatabaseManager
import bcrypt

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

@router.post("/login-working")
async def login_working(
    login_data: dict,
    db: DatabaseManager = Depends(get_database)
):
    """Working login endpoint with correct PostgreSQL syntax"""
    
    try:
        username = login_data.get("username")
        password = login_data.get("password")
        
        if not username or not password:
            raise HTTPException(status_code=400, detail={"error": "Missing credentials"})
        
        with db.get_cursor() as cursor:
            # Use %s for PostgreSQL (not ? for SQLite)
            cursor.execute("""
                SELECT id, username, email, password_hash, must_change_password, is_active
                FROM users 
                WHERE email = %s OR username = %s
            """, (username, username))
            
            result = cursor.fetchone()
            
            if not result:
                raise HTTPException(status_code=401, detail={"error": "Invalid credentials"})
            
            # Proper tuple unpacking
            user_id, db_username, email, password_hash, must_change_password, is_active = result
            
            # Check password
            if not bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8')):
                raise HTTPException(status_code=401, detail={"error": "Invalid credentials"})
            
            # Check if active
            if not is_active:
                raise HTTPException(status_code=401, detail={"error": "Account deactivated"})
            
            # Update last login
            cursor.execute("UPDATE users SET last_login = NOW() WHERE id = %s", (user_id,))
            db.connection.commit()
            
            # Check if password change required
            if must_change_password:
                return {
                    "success": False,
                    "must_change_password": True,
                    "message": "Password change required before accessing system",
                    "temporary_token": "temp_token_placeholder",
                    "user_id": user_id,
                    "email": email,
                    "username": db_username
                }
            
            # Normal successful login
            return {
                "success": True,
                "message": "Login successful",
                "access_token": "access_token_placeholder", 
                "user": {
                    "id": user_id,
                    "username": db_username,
                    "email": email,
                    "must_change_password": False
                }
            }
            
    except HTTPException:
        raise
    except Exception as e:
        import logging
        logging.error(f"Login error: {e}")
        raise HTTPException(status_code=500, detail={"error": f"Authentication failed: {str(e)}"})

