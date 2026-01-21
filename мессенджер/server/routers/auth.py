from fastapi import APIRouter, HTTPException
from datetime import datetime, timedelta
from database.user_model import UserModel  # Измененный импорт
from schemas.user import UserCreate, UserLogin, UserResponse
from passlib.context import CryptContext
import jwt
from database.db import init_db

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = "your-secret-key-here"

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(hours=24)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm="HS256")

@router.post("/register", response_model=UserResponse)
async def register(user: UserCreate):
    existing_user = UserModel.get_user_by_username(user.username)
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already exists")
    
    hashed_password = get_password_hash(user.password)
    
    # Автоматически делаем первого пользователя админом
    is_admin = False
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as count FROM users")
    user_count = cursor.fetchone()["count"]
    conn.close()
    
    if user_count == 0:  # Первый пользователь становится админом
        is_admin = True
    
    user_id = UserModel.create_user(user.username, hashed_password, is_admin)
    
    user_data = UserModel.get_user_by_id(user_id)
    return UserResponse(**user_data)

@router.post("/login")
async def login(user: UserLogin):
    user_data = UserModel.get_user_by_username(user.username)
    if not user_data or not verify_password(user.password, user_data["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    UserModel.update_user_status(user_data["id"], True, "online")
    
    access_token = create_access_token({"sub": user_data["username"]})
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/logout")
async def logout():
    return {"message": "Logout endpoint - implement later"}

# Добавим функцию для получения соединения с БД
def get_db_connection():
    import sqlite3
    from pathlib import Path
    DB_PATH = Path("messenger.db")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn