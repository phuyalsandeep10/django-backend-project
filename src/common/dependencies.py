from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from src.config.settings import settings
from datetime import datetime, timedelta
from src.common.base_repository import BaseRepository
from cachetools import TTLCache
from src.modules.auth.models import User
from src.config.database import get_session,  Session

# Initialize cache with 5-minute TTL and 1000-item capacity
user_cache = TTLCache(maxsize=1000, ttl=300)

security = HTTPBearer()

bearer_scheme = HTTPBearer()


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security),session:Session = Depends(get_session)):
    """Get current authenticated user"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        token = credentials.credentials.split(" ")[-1] if " " in credentials.credentials else credentials.credentials
        if(token in user_cache):
            return user_cache[token]
        
        
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=settings.ALGORITHM)

        user_email: str = payload.get("sub")
        user = BaseRepository(User,session=session).find_one({"email": user_email})
        # Check if user exists in cache





        if user is None:
            raise credentials_exception

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Inactive user",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
        if not user.email_verified_at:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Email not verified",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        user_cache[token] = user  # Cache the user object

        return user
    
    except JWTError as e:
        print("JWTError:", e)
        raise credentials_exception

def get_bearer_token(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    return credentials.credentials.split(" ")[-1] if " " in credentials.credentials else credentials.credentials
    
def update_user_cache(token: str, user: User):
    user_cache[token] = user

def invalidate_user_cache(token: str):
    user_cache.pop(token, None)

    
def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

