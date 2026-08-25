from datetime import datetime, timedelta
import sys
from typing import Any, Dict, Optional, cast
from fastapi import HTTPException, status
from jose import JWTError, jwt
from passlib.context import CryptContext
from pathlib import Path
import os
import secrets
import string
import logging
from dotenv import load_dotenv
import requests

try:
    from google.oauth2 import id_token
    from google.auth.transport import requests as google_requests
    _GOOGLE_OAUTH_AVAILABLE = True
except ImportError:
    id_token = None
    google_requests = None
    _GOOGLE_OAUTH_AVAILABLE = False

from app.models.schemas import GOOGLE_CLIENT_ID
from app.core.database import get_db_connection
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Generate a secure random secret key if none is provided
def generate_secure_secret_key(length: int = 64) -> str:
    """Generate a cryptographically secure random secret key"""
    alphabet = string.ascii_letters + string.digits + string.punctuation
    return ''.join(secrets.choice(alphabet) for _ in range(length))


# JWT Configuration
SECRET_KEY = os.getenv("SECRET_KEY") or generate_secure_secret_key()
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 30  # 30 days for regular users
ADMIN_TOKEN_EXPIRE_MINUTES = 60             # 60 minutes for admin sessions
SUPERADMIN_TOKEN_EXPIRE_MINUTES = 60        # 60 minutes for superadmin sessions
REFRESH_TOKEN_EXPIRE_DAYS = 90              # 90 days
REFRESH_SECRET_KEY = os.getenv("REFRESH_SECRET_KEY") or generate_secure_secret_key()

pwd_context = CryptContext(schemes=["bcrypt_sha256", "bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password"""
    # Bcrypt only supports passwords up to 72 bytes
    truncated_password = plain_password[:72]
    return pwd_context.verify(truncated_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hash a password for storing"""
    # Bcrypt only supports passwords up to 72 bytes
    truncated_password = password[:72]
    return pwd_context.hash(truncated_password)


def _get_session_timeout_for_role(role: str) -> int:
    """Read role-specific session timeout (minutes) from system_settings with defaults."""
    role_key = str(role or "user").lower()
    default_by_role = {
        "superadmin": SUPERADMIN_TOKEN_EXPIRE_MINUTES,
        "admin": ADMIN_TOKEN_EXPIRE_MINUTES,
        "user": ACCESS_TOKEN_EXPIRE_MINUTES,
    }
    setting_key_by_role = {
        "superadmin": "superadmin_session_timeout",
        "admin": "admin_session_timeout",
        "user": "user_session_timeout",
    }

    default_value = int(default_by_role.get(role_key, ACCESS_TOKEN_EXPIRE_MINUTES))
    setting_key = setting_key_by_role.get(role_key, "user_session_timeout")

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT setting_value FROM system_settings WHERE setting_key = %s",
            (setting_key,)
        )
        row = cursor.fetchone()

        # Backward compatibility fallback to legacy key
        if not row:
            cursor.execute(
                "SELECT setting_value FROM system_settings WHERE setting_key = %s",
                ("session_timeout",)
            )
            row = cursor.fetchone()

        cursor.close()
        if row and row.get("setting_value") is not None:
            parsed = int(cast(Dict[str, Any], row)["setting_value"])
            # Honor whatever system_settings says — only enforce a safety floor
            # so a misconfigured 0/negative value can't produce broken JWTs.
            return max(5, parsed)
    except Exception as e:
        logger.warning(f"Using default session timeout for role={role_key}: {e}")
    finally:
        if conn and conn.is_connected():
            conn.close()

    return default_value


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create a JWT access token with role-based expiry from system settings."""
    to_encode = data.copy()
    role = data.get("role", "user")
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        role_timeout = _get_session_timeout_for_role(str(role))
        expire = datetime.utcnow() + timedelta(minutes=role_timeout)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    username = data.get("sub", "unknown")
    print(f"🔑 Token generated for user '{username}' (role={role}): {encoded_jwt[:50]}...")
    return encoded_jwt

def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create a JWT refresh token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, REFRESH_SECRET_KEY, algorithm=ALGORITHM)
    username = data.get("sub", "unknown")
    print(f"🔄 Refresh token generated for user '{username}': {encoded_jwt[:50]}...")
    return encoded_jwt


def verify_token(token: str) -> Optional[str]:
    """Verify a JWT access token and return the username"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username is None:
            return None
        return str(username)
    except JWTError:
        return None


def verify_google_token(token: str) -> Dict[str, Any]:
    """Verify Google OAuth token and return user info"""
    if not _GOOGLE_OAUTH_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Google OAuth support is unavailable on this server"
        )
    try:
        logger.info(f"🔍 Verifying Google token with client ID: {GOOGLE_CLIENT_ID}")
        idinfo = id_token.verify_oauth2_token(
            token, google_requests.Request(), GOOGLE_CLIENT_ID
        )

        # Verify issuer
        if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
            logger.error(f"❌ Wrong issuer: {idinfo['iss']}")
            raise HTTPException(status_code=400, detail="Wrong issuer")

        # Verify audience (client ID)
        if idinfo['aud'] != GOOGLE_CLIENT_ID:
            logger.error(f"❌ Wrong audience. Expected: {GOOGLE_CLIENT_ID}, Got: {idinfo['aud']}")
            raise HTTPException(status_code=400, detail="Wrong audience")

        logger.info(f"✅ Google token verified for user: {idinfo.get('email')}")
        return idinfo
    except ValueError as e:
        logger.error(f"❌ ValueError during Google token verification: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Invalid Google token: {str(e)}")
    except Exception as e:
        logger.error(f"❌ Unexpected error during Google token verification: {str(e)}", exc_info=True)
        raise HTTPException(status_code=400, detail=f"Google authentication failed: {str(e)}")
    
def generate_username(email: str, first_name: str, last_name: str) -> str:
    """Generate a unique username from email or name"""
    base_username = email.split('@')[0]
    random_suffix = ''.join(secrets.choice(string.digits) for _ in range(4))
    return f"{base_username}_{random_suffix}"


async def download_profile_picture(picture_url: str, username: str) -> Optional[str]:
    """Download and save Google profile picture"""
    try:
        import aiohttp
        import aiofiles
        
        # Create profile pictures directory
        profile_dir = Path("static/profile_pictures")
        profile_dir.mkdir(exist_ok=True)
        
        # Generate filename
        file_extension = Path(picture_url).suffix.split('?')[0] or '.jpg'
        filename = f"{username}{file_extension}"
        filepath = profile_dir / filename
        
        # Download image
        async with aiohttp.ClientSession() as session:
            async with session.get(picture_url) as response:
                if response.status == 200:
                    async with aiofiles.open(filepath, 'wb') as f:
                        await f.write(await response.read())
                    
                    return f"profile_pictures/{filename}"
        
        return None
    except Exception as e:
        print(f"Failed to download profile picture: {e}")
        return None


async def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """Get user by email from database"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM users_info WHERE email = %s", (email,))
        user = cursor.fetchone()
        # Cast the result to the expected type
        return cast(Optional[Dict[str, Any]], user)
    except Exception as e:
        logger.error(f"Error getting user by email: {e}")
        return None
    finally:
        cursor.close()
        conn.close()


async def update_user_last_login(user_id: int) -> None:
    """Update user's last login timestamp"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE users_info SET last_login = NOW() WHERE id = %s",
            (user_id,)
        )
        conn.commit()
    except Exception as e:
        logger.error(f"Error updating user last login: {e}")
    finally:
        cursor.close()
        conn.close()


async def create_user(user_data: Dict[str, Any]) -> int:
    """Create a new user and return the user ID"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Generate a random password hash for Google OAuth users
        password_hash = get_password_hash(secrets.token_urlsafe(32))
        
        cursor.execute("""
            INSERT INTO users_info (
                email, first_name, last_name, username, profile_picture,
                home_area, phone_number, password_hash, is_verified,
                created_at, last_login
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            user_data['email'],
            user_data['first_name'],
            user_data['last_name'],
            user_data['username'],
            user_data.get('profile_picture'),
            user_data.get('home_area'),
            user_data.get('phone_number'),
            password_hash,
            user_data.get('email_verified', True),
            user_data['created_at'],
            user_data['last_login']
        ))
        
        conn.commit()
        user_id = cursor.lastrowid
        if user_id is None:
            raise Exception("Failed to get user ID after insertion")
        return user_id
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


async def handle_google_auth(google_data: Dict[str, Any], is_registration: bool = False, additional_data: Optional[Dict] = None):
    """Handle Google authentication for both login and registration"""
    
    email = google_data['email']
    first_name = google_data.get('given_name', '')
    last_name = google_data.get('family_name', '')
    picture_url = google_data.get('picture')
    
    # Check if user exists
    user = await get_user_by_email(email)
    
    if user:
        # Existing user - login
        if is_registration:
            raise HTTPException(status_code=400, detail="User already exists")
        
        # Update last login
        await update_user_last_login(user['id'])
        
        # Generate JWT token
        token_data = {
            "sub": str(user['id']),
            "email": user['email'],
            "exp": datetime.utcnow() + timedelta(days=7)
        }
        token = jwt.encode(token_data, os.getenv("JWT_SECRET", SECRET_KEY), algorithm="HS256")
        
        return {
            "access_token": token,
            "token_type": "bearer",
            "user": user,
            "is_new_user": False
        }
    else:
        # New user - registration
        if not is_registration:
            raise HTTPException(status_code=404, detail="User not found. Please register first.")
        
        # Generate username
        username = generate_username(email, first_name, last_name)
        
        # Download profile picture
        profile_picture = None
        if picture_url:
            profile_picture = await download_profile_picture(picture_url, username)
        
        # Use additional data from registration form if provided
        if additional_data:
            first_name = additional_data.get('first_name', first_name)
            last_name = additional_data.get('last_name', last_name)
            home_area = additional_data.get('home_area')
            phone_number = additional_data.get('phone_number')
        else:
            home_area = None
            phone_number = None
        
        # Create user in database
        user_data = {
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "username": username,
            "profile_picture": profile_picture,
            "home_area": home_area,
            "phone_number": phone_number,
            "is_google_oauth": True,
            "email_verified": True,  # Google emails are verified
            "created_at": datetime.utcnow(),
            "last_login": datetime.utcnow()
        }
        
        user_id = await create_user(user_data)
        user_data['id'] = user_id
        
        # Generate JWT token
        token_data = {
            "sub": str(user_id),
            "email": email,
            "exp": datetime.utcnow() + timedelta(days=7)
        }
        token = jwt.encode(token_data, os.getenv("JWT_SECRET", SECRET_KEY), algorithm=ALGORITHM)
        
        return {
            "access_token": token,
            "token_type": "bearer",
            "user": user_data,
            "is_new_user": True
        }

def verify_refresh_token(token: str) -> Optional[str]:
    """Verify a JWT refresh token and return the username"""
    try:
        payload = jwt.decode(token, REFRESH_SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username is None:
            return None
        return str(username)
    except JWTError:
        return None


def generate_email_verification_token() -> str:
    return secrets.token_urlsafe(32)

def generate_password_reset_token() -> str:
    return secrets.token_urlsafe(32)

# def verify_google_token(token: str) -> dict:
#     """Verify Google OAuth token and return user info"""
#     try:
#         # Get Google client ID from environment
#         google_client_id = os.getenv("GOOGLE_CLIENT_ID")
#         if not google_client_id:
#             print("❌ GOOGLE_CLIENT_ID not found in environment variables")
#             raise HTTPException(status_code=500, detail="Google OAuth not configured")

#         print(f"🔧 Verifying Google token with client ID: {google_client_id}")

#         # Verify the token
#         idinfo = id_token.verify_oauth2_token(token, google_requests.Request(), google_client_id)

#         # Check if the token is issued by Google
#         if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
#             raise ValueError('Wrong issuer.')

#         # Check audience
#         if idinfo['aud'] != google_client_id:
#             raise ValueError('Wrong audience.')

#         print(f"✅ Google token verified for user: {idinfo.get('email')}")

#         return {
#             'sub': idinfo['sub'],  # Google's unique user ID
#             'email': idinfo.get('email'),
#             'email_verified': idinfo.get('email_verified', False),
#             'name': idinfo.get('name'),
#             'given_name': idinfo.get('given_name'),
#             'family_name': idinfo.get('family_name'),
#             'picture': idinfo.get('picture'),
#             'locale': idinfo.get('locale')
#         }
#     except ValueError as e:
#         print(f"❌ Invalid Google token: {str(e)}")
#         raise HTTPException(status_code=401, detail=f"Invalid Google token: {str(e)}")
#     except Exception as e:
#         print(f"❌ Google token verification failed: {str(e)}")
#         raise HTTPException(status_code=500, detail=f"Google token verification failed: {str(e)}")
    
def create_or_get_google_user(google_user_info: dict, conn):
    """Create or get user from Google OAuth info with enhanced error handling"""
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        logger.info(f"🔍 [BACKEND] create_or_get_google_user started")

        # Check if user exists by Google ID
        cursor.execute("SELECT * FROM users_info WHERE google_id = %s", (google_user_info['sub'],))
        user = cursor.fetchone()
        
        if user:
            logger.info(f"✅ [BACKEND] Found existing user by Google ID: {user.get('username')}")
            # Update user info
            cursor.execute("""
                UPDATE users_info SET 
                email = %s, first_name = %s, last_name = %s, profile_picture = %s,
                last_login = NOW(), email_verified = %s, is_verified = %s
                WHERE google_id = %s
            """, (
                google_user_info.get('email'),
                google_user_info.get('given_name'),
                google_user_info.get('family_name'), 
                google_user_info.get('picture'),
                google_user_info.get('email_verified', False),
                1,
                google_user_info['sub']
            ))
            conn.commit()
            return user

        # Check if user exists by email
        if google_user_info.get('email'):
            cursor.execute("SELECT * FROM users_info WHERE email = %s", (google_user_info['email'],))
            existing_user = cursor.fetchone()
            
            if existing_user:
                logger.info(f"✅ [BACKEND] Linking Google to existing user: {existing_user.get('username')}")
                cursor.execute("""
                    UPDATE users_info SET 
                    google_id = %s, profile_picture = %s, email_verified = %s, last_login = NOW()
                    WHERE email = %s
                """, (
                    google_user_info['sub'],
                    google_user_info.get('picture'),
                    google_user_info.get('email_verified', False),
                    google_user_info['email']
                ))
                conn.commit()
                return existing_user

        # Create new user
        email = google_user_info.get('email')
        base_username = email.split('@')[0] if email else f"google_user_{google_user_info['sub'][:8]}"
        username = base_username
        
        # Ensure unique username
        counter = 1
        while True:
            cursor.execute("SELECT COUNT(*) as count FROM users_info WHERE username = %s", (username,))
            if cursor.fetchone()['count'] == 0:
                break
            username = f"{base_username}_{counter}"
            counter += 1

        # Generate password and hash
        random_password = secrets.token_urlsafe(32)
        hashed_password = get_password_hash(random_password)

        logger.info(f"✅ [BACKEND] Creating new user: {username}")

        # Insert new user
        cursor.execute("""
            INSERT INTO users_info (
                username, email, password_hash, first_name, last_name,
                google_id, profile_picture, email_verified, is_verified, role,
                created_at, last_login
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
        """, (
            username,
            google_user_info.get('email'),
            hashed_password,
            google_user_info.get('given_name'),
            google_user_info.get('family_name'),
            google_user_info['sub'],
            google_user_info.get('picture'),
            google_user_info.get('email_verified', False),
            1,
            'user'
        ))

        conn.commit()

        # Get the created user
        cursor.execute("SELECT * FROM users_info WHERE google_id = %s", (google_user_info['sub'],))
        new_user = cursor.fetchone()

        logger.info(f"✅ [BACKEND] User created successfully: {new_user.get('username')}")
        return new_user

    except Exception as e:
        logger.error(f"❌ [BACKEND] Error in create_or_get_google_user: {str(e)}", exc_info=True)
        # Don't swallow the exception
        raise
    finally:
        if cursor:
            cursor.close()