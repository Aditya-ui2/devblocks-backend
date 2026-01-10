from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

# Apne modules
import schemas
import models
from database import get_db

class TokenData(BaseModel):
    email: Optional[str] = None
# --- CONFIGURATION ---
# Is key ko production me safe rakhna
SECRET_KEY = "healthconnect_secret_key_change_me_later" 
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# --- PASSWORD CONTEXT ---
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
# Dhyan rakhna: tokenUrl wahi hona chahiye jo main.py me login route ho
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login") 

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

# --- JWT TOKEN GENERATOR ---
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# --- CURRENT USER DEPENDENCY (Protection ke liye) ---
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # 1. Token Decode karo
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        # 2. Email nikalo ('sub' key se)
        email: str = payload.get("sub")

        if email is None:
            raise credentials_exception
        
        # 3. TokenData schema mein daalo
        token_data = schemas.TokenData(email=email) 

    except JWTError:
        raise credentials_exception

    # 4. Database mein user dhundo (EMAIL se)
    user = db.query(models.User).filter(models.User.email == token_data.email).first()

    if user is None:
        raise credentials_exception

    return user