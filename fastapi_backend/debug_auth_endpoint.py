from fastapi import APIRouter, HTTPException, Depends
from api.dependencies import get_database
from api.database import DatabaseManager
import bcrypt

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

@router.post("/login-debug")
async def login_debug(
    login_data: dict,
    db: DatabaseManager = Depends(get_database)
):
    """Debug version that shows what's happening with cursor data"""
    
    try:
        username = login_data.get("username")
        password = login_data.get("password")
        
        if not username or not password:
            raise HTTPException(status_code=400, detail={"error": "Missing credentials"})
        
        with db.get_cursor() as cursor:
            cursor.execute("""
                SELECT id, username, email, password_hash, must_change_password, is_active
                FROM users 
                WHERE email = %s OR username = %s
            """, (username, username))
            
            result = cursor.fetchone()
            
            if not result:
                return {
                    "debug": "user_not_found",
                    "searched_for": username
                }
            
            # Debug: Show what we got from database
            debug_info = {
                "debug": "database_result",
                "result_type": str(type(result)),
                "result_length": len(result) if result else 0,
            }
            
            # Try different ways to access the data
            try:
                if hasattr(result, '_asdict'):
                    # Named tuple
                    debug_info["access_method"] = "named_tuple"
                    user_data = result._asdict()
                    user_id = user_data['id']
                    db_username = user_data['username']
                    email = user_data['email']
                    password_hash = user_data['password_hash']
                    must_change_password = user_data['must_change_password']
                    is_active = user_data['is_active']
                elif isinstance(result, dict):
                    # Dictionary
                    debug_info["access_method"] = "dictionary"
                    user_id = result['id']
                    db_username = result['username']
                    email = result['email']
                    password_hash = result['password_hash']
                    must_change_password = result['must_change_password']
                    is_active = result['is_active']
                else:
                    # Tuple
                    debug_info["access_method"] = "tuple"
                    user_id, db_username, email, password_hash, must_change_password, is_active = result
                
                debug_info["user_id"] = str(user_id)
                debug_info["username"] = db_username
                debug_info["email"] = email
                debug_info["password_hash_length"] = len(password_hash) if password_hash else 0
                debug_info["password_hash_start"] = password_hash[:20] if password_hash else "None"
                debug_info["must_change_password"] = must_change_password
                debug_info["is_active"] = is_active
                
                # Test password verification
                try:
                    password_match = bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
                    debug_info["password_verification"] = "success" if password_match else "failed"
                    
                    if password_match:
                        if must_change_password:
                            return {
                                "success": False,
                                "must_change_password": True,
                                "message": "Password change required",
                                "user_id": str(user_id),
                                "email": email,
                                "debug": debug_info
                            }
                        else:
                            return {
                                "success": True,
                                "message": "Login successful",
                                "user_id": str(user_id),
                                "email": email,
                                "debug": debug_info
                            }
                    else:
                        return {
                            "success": False,
                            "error": "Invalid credentials",
                            "debug": debug_info
                        }
                        
                except Exception as bcrypt_error:
                    debug_info["bcrypt_error"] = str(bcrypt_error)
                    return {
                        "success": False,
                        "error": f"Password verification failed: {bcrypt_error}",
                        "debug": debug_info
                    }
                    
            except Exception as access_error:
                debug_info["access_error"] = str(access_error)
                return {
                    "success": False,
                    "error": f"Data access failed: {access_error}",
                    "debug": debug_info
                }
            
    except Exception as e:
        return {
            "success": False,
            "error": f"Debug endpoint error: {str(e)}",
            "debug": {"exception": str(e)}
        }

