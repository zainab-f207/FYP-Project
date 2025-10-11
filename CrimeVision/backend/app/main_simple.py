# from fastapi import FastAPI, HTTPException, Depends
# from pydantic import BaseModel, Field
# import mysql.connector
# from mysql.connector import Error
# from fastapi.middleware.cors import CORSMiddleware
# from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
# from datetime import timedelta
# from auth_updated import verify_password, get_password_hash, create_access_token, verify_token
# from dotenv import load_dotenv
# import os
# import logging
# from datetime import datetime
# import re

# load_dotenv()

# # Configure logging
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

# # CORS configuration
# ALLOWED_ORIGINS_STR = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173, http://localhost:5174, http://127.0.0.1:5173, http://127.0.0.1:5174")
# ALLOWED_ORIGINS = [origin.strip() for origin in ALLOWED_ORIGINS_STR.split(",")]

# # Database config
# DB_CONFIG = {
#     "host": os.getenv("DB_HOST", "localhost"),
#     "user": os.getenv("DB_USER", "root"),
#     "password": os.getenv("DB_PASSWORD", "hafsa555"),
#     "database": os.getenv("DB_NAME", "crimevision_db"),
#     "port": int(os.getenv("DB_PORT", 3306)),
# }

# # Authentication models
# class UserRegister(BaseModel):
#     first_name: str = Field(..., min_length=1, max_length=50, description="First name")
#     last_name: str = Field(..., min_length=1, max_length=50, description="Last name")
#     email: str = Field(..., description="Email address")
#     password: str = Field(..., min_length=6, description="Password")
#     home_area: str = Field(None, description="User's home area")

# class UserLogin(BaseModel):
#     username: str = Field(..., description="Username")
#     password: str = Field(..., description="Password")

# class Token(BaseModel):
#     access_token: str
#     token_type: str

# # JWT Security
# security = HTTPBearer()

# # Helper Functions
# def generate_username(first_name: str, last_name: str) -> str:
#     """Generate username from first name and last name"""
#     base_username = f"{first_name.lower()}.{last_name.lower()}"
#     username = base_username

#     # Check if username already exists and add number if needed
#     conn = get_db_connection()
#     cursor = conn.cursor()

#     try:
#         counter = 1
#         while True:
#             cursor.execute("SELECT id FROM users_info WHERE username = %s", (username,))
#             if not cursor.fetchone():
#                 break
#             username = f"{base_username}{counter}"
#             counter += 1
#     except Error as e:
#         logger.error(f"Database error checking username: {e}")
#     finally:
#         cursor.close()
#         conn.close()

#     return username

# def validate_name(name: str) -> str:
#     """Validate and sanitize name input"""
#     sanitized = re.sub(r'[^\w\s\-_]', '', name.strip())
#     if not sanitized:
#         raise HTTPException(status_code=400, detail="Invalid name format")
#     return sanitized[:50]

# def get_db_connection():
#     """Create a new DB connection each time"""
#     try:
#         conn = mysql.connector.connect(**DB_CONFIG)
#         if conn.is_connected():
#             return conn
#         else:
#             raise HTTPException(status_code=500, detail="Failed to connect to database")
#     except Error as e:
#         logger.error(f"Database connection failed: {e}")
#         raise HTTPException(status_code=500, detail="Database connection failed")

# # Create users table if it doesn't exist
# def create_users_table():
#     """Create users_info table for authentication with first_name and last_name"""
#     conn = get_db_connection()
#     cursor = conn.cursor()
#     try:
#         cursor.execute("""
#             CREATE TABLE IF NOT EXISTS users_info (
#                 id INT AUTO_INCREMENT PRIMARY KEY,
#                 username VARCHAR(50) UNIQUE NOT NULL,
#                 first_name VARCHAR(50) NOT NULL,
#                 last_name VARCHAR(50) NOT NULL,
#                 email VARCHAR(100) UNIQUE NOT NULL,
#                 password_hash VARCHAR(255) NOT NULL,
#                 home_area VARCHAR(100),
#                 created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
#             )
#         """)
#         conn.commit()
#         logger.info("Users_info table created successfully")
#     except Error as e:
#         logger.error(f"Error creating users_info table: {e}")
#         raise HTTPException(status_code=500, detail="Database error")
#     finally:
#         cursor.close()
#         conn.close()

# # Initialize tables on startup
# create_users_table()

# # FastAPI app
# app = FastAPI(title="CrimeVision API - Simple Version")

# # CORS middleware
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["http://localhost:5173"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=ALLOWED_ORIGINS,
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# @app.get("/")
# def root():
#     return {"message": "Welcome to CrimeVision API - Simple Version"}

# @app.get("/test-db")
# def test_db():
#     """Test database connection"""
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         cursor.execute("SELECT 1")
#         result = cursor.fetchone()
#         cursor.close()
#         conn.close()
#         return {"database": "connected", "result": result}
#     except Error as e:
#         return {"database": "error", "message": str(e)}

# # Authentication endpoints
# @app.post("/auth/register", response_model=Token)
# def register(user: UserRegister):
#     """Register a new user with auto-generated username"""
#     conn = get_db_connection()
#     cursor = conn.cursor()
#     try:
#         # Validate names
#         first_name = validate_name(user.first_name)
#         last_name = validate_name(user.last_name)

#         # Generate username from first and last name
#         username = generate_username(first_name, last_name)

#         # Check if email already exists
#         cursor.execute("SELECT id FROM users_info WHERE email = %s", (user.email,))
#         if cursor.fetchone():
#             raise HTTPException(status_code=400, detail="Email already exists")

#         # Hash password
#         password_hash = get_password_hash(user.password)

#         # Create user
#         cursor.execute(
#             "INSERT INTO users_info (username, first_name, last_name, email, password_hash, home_area) VALUES (%s, %s, %s, %s, %s, %s)",
#             (username, first_name, last_name, user.email, password_hash, user.home_area)
#         )
#         conn.commit()

#         # Create access token
#         access_token = create_access_token(data={"sub": username})
#         return {
#             "access_token": access_token,
#             "token_type": "bearer",
#             "username": username,
#             "message": f"User registered successfully. Your username is: {username}"
#         }

#     except Error as e:
#         logger.error(f"Database error during registration: {e}")
#         raise HTTPException(status_code=500, detail="Database error")
#     finally:
#         cursor.close()
#         conn.close()

# @app.post("/auth/login", response_model=Token)
# def login(user: UserLogin):
#     """Login user and return JWT token"""
#     conn = get_db_connection()
#     cursor = conn.cursor(dictionary=True)
#     try:
#         # Get user from database
#         cursor.execute("SELECT username, password_hash FROM users_info WHERE username = %s", (user.username,))
#         db_user = cursor.fetchone()

#         if not db_user:
#             raise HTTPException(status_code=401, detail="Invalid credentials")

#         # Verify password
#         password_hash = db_user.get("password_hash", "")
#         if not verify_password(user.password, password_hash):
#             raise HTTPException(status_code=401, detail="Invalid credentials")

#         # Create access token
#         access_token = create_access_token(data={"sub": user.username})
#         return {"access_token": access_token, "token_type": "bearer"}

#     except Error as e:
#         logger.error(f"Database error during login: {e}")
#         raise HTTPException(status_code=500, detail="Database error")
#     finally:
#         cursor.close()
#         conn.close()

# def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
#     """Get current user from JWT token"""
#     token = credentials.credentials
#     username = verify_token(token)
#     if username is None:
#         raise HTTPException(status_code=401, detail="Invalid token")
#     return username

# @app.get("/auth/me")
# def get_current_user_info(current_user: str = Depends(get_current_user)):
#     """Get current user information"""
#     conn = get_db_connection()
#     cursor = conn.cursor(dictionary=True)
#     try:
#         cursor.execute("SELECT username, first_name, last_name, email, home_area, created_at FROM users_info WHERE username = %s", (current_user,))
#         user = cursor.fetchone()

#         if not user:
#             raise HTTPException(status_code=404, detail="User not found")

#         return {
#             "username": user.get("username", ""),
#             "first_name": user.get("first_name", ""),
#             "last_name": user.get("last_name", ""),
#             "email": user.get("email", ""),
#             "home_area": user.get("home_area"),
#             "created_at": user.get("created_at", "")
#         }

#     except Error as e:
#         logger.error(f"Database error getting user info: {e}")
#         raise HTTPException(status_code=500, detail="Database error")
#     finally:
#         cursor.close()
#         conn.close()

# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=8000)
