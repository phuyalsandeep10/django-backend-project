from fastapi import APIRouter, HTTPException
from jose import jwt
from datetime import datetime, timedelta
from src.common.dependencies import get_current_user
from fastapi import Depends
from src.common.dependencies import create_access_token
from .dto import LoginDto, RegisterDto, VerifyEmailTokenDto,ForgotPasswordVerifyDto, VerifyEmailDto, ResetPasswordDto, RefreshTokenDto
from .models import User, EmailVerification, RefreshToken
from src.common.base_repository import BaseRepository
from src.config.database import get_session, Session
from src.common.utils import generate_numeric_token, compare_password, hash_password, generate_refresh_token
from src.modules.organizations.models import OrganizationInvitation


router = APIRouter()


@router.post("/login")
def login(request: LoginDto, session: Session = Depends(get_session)):
    user = BaseRepository(User, session).find_one({
        "email": request.email
    })

    # Check if user exists
    if not user:
        raise HTTPException(status_code=401, detail="Email not found")
    
    if not compare_password(user.password, request.password):
        raise HTTPException(status_code=401, detail="Invalid password")
    
    token = create_access_token({"sub": user.email})
    refresh_token = generate_refresh_token()
    BaseRepository(RefreshToken, session).create({
        "user_id": user.id,
        "token": refresh_token,
        "active": True,
        "created_at": datetime.utcnow(),
        "expires_at": datetime.utcnow() + timedelta(days=30)
    })
    return {"access_token": token, "refresh_token": refresh_token}



@router.post("/logout")
def logout(session: Session = Depends(get_session), user=Depends(get_current_user)):
    # Invalidate the refresh token
    token_data = BaseRepository(RefreshToken, session).find_one({
        "user_id": user.id,
        "active": True
    })
    if not token_data:
        raise HTTPException(status_code=404, detail="No active refresh token found")
    # Mark the token as inactive
    BaseRepository(RefreshToken, session).update(token_data.id, {"active": False})
    return {"message": "Logged out successfully"}

@router.post("/refresh-token")
def refresh_token(body:RefreshTokenDto, session: Session = Depends(get_session)):
    # Validate the refresh token
    token_data = BaseRepository(RefreshToken, session).find_one({
        "token": body.token,
        "active": True,
        
    })
    if not token_data:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
    
    # Check if the refresh token has expired
    expires_at = token_data.expires_at
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)

    # If the token has expired, raise an error
    if expires_at < datetime.utcnow():
        raise HTTPException(status_code=401, detail="Refresh token has expired")
    

    # Create a new access token
    try:
        user = BaseRepository(User, session).findById(token_data.user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        access_token = create_access_token({"sub": user.email})
        return {"access_token": access_token}
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

@router.post("/register")
def register(request: RegisterDto, session: Session = Depends(get_session)):
    repository = BaseRepository(User, session)
    user = repository.find_one({
        "email": request.email
    })
    # Check if user already exists

    if user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_password =  hash_password(request.password)

    user = repository.create(data={
        "email": request.email,
        "name": request.name,
        "password": hashed_password
    
    })

    token = generate_numeric_token(6)
    # Here you would typically send a verification email
    BaseRepository(EmailVerification, session).create(
        data={
            "user_id": user.id,
            "token": token,
            "is_used": False,
            "created_at": datetime.utcnow(),
            "expires_at": datetime.utcnow() + timedelta(days=1),
            "type": "email_verification"
        }
        
    )
    
    return {"message": "User registered successfully"}

@router.get("/me")
def get_auth_user(user=Depends(get_current_user), session: Session = Depends(get_session)):
    try:
        user = BaseRepository(User,session=session).findById(user.id)
        del user.password  # Remove password from the response
        return user
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    

@router.post("/verify-email")
def verify_email_token(body:VerifyEmailTokenDto, session: Session = Depends(get_session)):
    user_repo = BaseRepository(User, session)
    
    user = user_repo.find_one({
            "email": body.email
        })
        
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    

    
    
    verification_repo = BaseRepository(EmailVerification, session)
    print(body.token)
    verification = verification_repo.find_one({"token": body.token, "is_used": False,"user_id":user.id})
    

    if not verification:
        raise HTTPException(status_code=400, detail="Invalid or expired verification token")
    
    expires_at = verification.expires_at
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)

    if expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Verification token has expired")
    # Mark the token as used
    verification_repo.update(verification.id, {"is_used": True})
    # Here you would typically update the user's email verification status
    user_repo.update(user.id, {"email_verified_at": datetime.utcnow()})

    return {"message": "Email verified successfully"}

@router.post("/reset-password")
def reset_password(body:ResetPasswordDto, user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    user = BaseRepository(User, session).find_one({
        "email": user.email
    })
    if not user:
        raise HTTPException(status_code=404, detail="Email not found")
    
    # Generate a reset token (in a real application, you would send this to the user's email)
    password = user.password
    if not compare_password(password, body.old_password):
        raise HTTPException(status_code=400, detail="Old password is incorrect")
    
    # Update the user's password
    new_hashed_password = hash_password(body.new_password)

    BaseRepository(User, session).update(user.id, {"password": new_hashed_password})
    
    # Here you would typically send a reset link to the user's email
    return {"message": "Password reset link sent to your email"}

@router.post("/forgot-password-request")
def forgot_password_request(body: VerifyEmailDto, session: Session = Depends(get_session)):
    user = BaseRepository(User, session=session).find_one({
        "email": body.email
    })

    # Check if user exists
    if not user:
        raise HTTPException(status_code=404, detail="Email not found")
    # Generate a reset token (in a real application, you would send this to the user's email)
    token = generate_numeric_token(6)

    # Store the token in the database (or send it via email)
    BaseRepository(EmailVerification, session).create(
        data={
            "user_id": user.id,
            "token": token,
            "is_used": False,
            "created_at": datetime.utcnow(),
            "expires_at": datetime.utcnow() + timedelta(hours=1),
            "type": "forgot_password"
        }
    )
    # For simplicity, we are just returning the token here


   
    # Here you would typically send a reset link to the user's email
    return {"message": "Password reset link sent to your email"}

@router.post("/forgot-password-verify")
def forgot_password_verify(body:ForgotPasswordVerifyDto, session: Session = Depends(get_session)):
    user_repo = BaseRepository(User, session=session)
    user = user_repo.find_one({
        "email": body.email
    })

    if not user:
        raise HTTPException(status_code=404, detail="Email not found")
    
    # Check if the token is valid
    verification_repo = BaseRepository(EmailVerification, session=session)

    verification = verification_repo.find_one({"token": body.token, "is_used": False, "user_id": user.id})

    if not verification:
        raise HTTPException(status_code=400, detail="Invalid or expired verification token")

    expires_at = verification.expires_at
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)

    # Check if the token has expired
    if expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Verification token has expired")
    
    # Mark the token as used
    verification_repo.update(verification.id, {"is_used": True})
    # Update the user's password

    user_repo.update(user.id, {"password": hash_password(body.new_password)})
    return {"message": "Password reset successfully"}



@router.get('/invitations')
def get_invitations(user=Depends(get_current_user)):
    return OrganizationInvitation.filter(where={
        "email":user.email
    })