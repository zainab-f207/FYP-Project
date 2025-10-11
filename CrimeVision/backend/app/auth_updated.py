from datetime import datetime, timedelta
from typing import Optional
from fastapi import HTTPException, status
from jose import JWTError, jwt
from passlib.context import CryptContext
import os
import secrets
import string
from dotenv import load_dotenv

load_dotenv()

# Generate a secure random secret key if none is provided
def generate_secure_secret_key(length: int = 64) -> str:
    """Generate a cryptographically secure random secret key"""
    alphabet = string.ascii_letters + string.digits + string.punctuation
    return ''.join(secrets.choice(alphabet) for _ in range(length))

# JWT Configuration
SECRET_KEY = os.getenv("SECRET_KEY") or generate_secure_secret_key()
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

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

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create a JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    # Console message when token is generated
    username = data.get("sub", "unknown")
    print(f"🔑 Token generated for user '{username}': {encoded_jwt[:50]}...")

    return encoded_jwt

def verify_token(token: str) -> Optional[str]:
    """Verify a JWT token and return the username"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
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

