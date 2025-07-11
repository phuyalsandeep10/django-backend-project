from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from jose import jwt
from datetime import datetime, timedelta
from src.common.dependencies import get_current_user
from fastapi import Depends
from src.common.dependencies import create_access_token
from .dto import LoginDto, RegisterDto, VerifyEmailTokenDto,ForgotPasswordVerifyDto, VerifyEmailDto, ResetPasswordDto, RefreshTokenDto
from .models import User, EmailVerification, RefreshToken

from src.config.database import get_session, Session
from src.common.utils import generate_numeric_token, compare_password, hash_password, generate_refresh_token
from src.modules.organizations.models import OrganizationInvitation
from src.config.mail import mail_sender
from src.tasks import send_verification_email, send_forgot_password_email
from .social_auth import oauth
from src.config.settings import settings


router = APIRouter()


def create_token(user):
    token = create_access_token(data={"sub": user.email})
    refresh_token = generate_refresh_token()

    RefreshToken.create(
        user_id=user.id,
        token=refresh_token,
        active=True,
        created_at=datetime.utcnow(),
        expires_at=datetime.utcnow() + timedelta(days=30)
    )


    return {"access_token": token, "refresh_token": refresh_token}

@router.post("/login")
def login(request: LoginDto):
    
    user = User.find_one(where={
        "email":request.email
    })

    # Check if user exists
    if not user:
        raise HTTPException(status_code=401, detail="Email not found")
    
    if not compare_password(user.password, request.password):
        raise HTTPException(status_code=401, detail="Invalid password")
    
    



    return create_token(user)



@router.post("/logout")
def logout( user=Depends(get_current_user)):
    # Invalidate the refresh token

    token_data = RefreshToken.find_one(where={
        "user_id":user.id,
        "active":True
    })


    if not token_data:
        raise HTTPException(status_code=404, detail="No active refresh token found")
    # Mark the token as inactive
    RefreshToken.update(token_data.id,active=False)





    

    return {"message": "Logged out successfully"}

@router.post("/refresh-token")
def refresh_token(body:RefreshTokenDto, session: Session = Depends(get_session)):
    # Validate the refresh token
    token_data = RefreshToken.find_one(where={
        "token":body.token,
        "active":True
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
        user = User.get(token_data.user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        access_token = create_access_token(data={"sub": user.email})
        return {"access_token": access_token}
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

@router.post("/register")
def register(request: RegisterDto, session: Session = Depends(get_session)):
   
    user = User.find_one({
        "email":request.email
    })
   
    # Check if user already exists

    if user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_password =  hash_password(request.password)
    user = User.create(email=request.email,name=request.name,password=hashed_password)

    token = generate_numeric_token(6)
    # Here you would typically send a verification email

    EmailVerification.create(
        user_id=user.id,
        token=token,
        is_used=False,
        expires_at=datetime.utcnow()+timedelta(days=1),
        type="email_verification"
    )

    send_verification_email.delay(email=request.email, token=token)
   
    
    return {"message": "User registered successfully"}

@router.get("/me")
def get_auth_user(user=Depends(get_current_user), session: Session = Depends(get_session)):
    try:
        user = User.get(user.id)
        del user.password  # Remove password from the response
        return user
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    

@router.post("/verify-email")
def verify_email_token(body:VerifyEmailTokenDto, session: Session = Depends(get_session)):
 
    
    user = User.find_one({
            "email": body.email
        })
        
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    

    verification = EmailVerification.find_one({
        "token":body.token,
        "is_used":False,
        "user_id":user.id
    })
    

    if not verification:
        raise HTTPException(status_code=400, detail="Invalid or expired verification token")
    
    expires_at = verification.expires_at
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)

    if expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Verification token has expired")
    # Mark the token as used
    EmailVerification.update(verification.id, is_used=True)
    # Here you would typically update the user's email verification status
    User.update(user.id, email_verified_at=datetime.utcnow())

    return {"message": "Email verified successfully"}

@router.post("/reset-password")
def reset_password(body:ResetPasswordDto, user: User = Depends(get_current_user), session: Session = Depends(get_session)):
 
    user = User.find_one({
        "email":user.email
    })
    if not user:
        raise HTTPException(status_code=404, detail="Email not found")
    
    # Generate a reset token (in a real application, you would send this to the user's email)
    password = user.password
    if not compare_password(password, body.old_password):
        raise HTTPException(status_code=400, detail="Old password is incorrect")
    
    # Update the user's password
    new_hashed_password = hash_password(body.new_password)

    User.update(user.id, password=new_hashed_password)
    
    # Here you would typically send a reset link to the user's email
    return {"message": "Password reset successfully"}

@router.post("/forgot-password-request")
def forgot_password_request(body: VerifyEmailDto, session: Session = Depends(get_session)):
    user = User.find_one({
        "email":body.email
    })

    # Check if user exists
    if not user:
        raise HTTPException(status_code=404, detail="Email not found")
    # Generate a reset token (in a real application, you would send this to the user's email)
    token = generate_numeric_token(6)

    # Store the token in the database (or send it via email)

    EmailVerification.create(
        user_id=user.id,
        token=token,
        is_used=False,
        expires_at=(datetime.utcnow()+timedelta(hours=1)),
        type="forgot_password"
    )
    send_forgot_password_email.delay(email=body.email, token=token)

    

    # For simplicity, we are just returning the token here
   
    # Here you would typically send a reset link to the user's email
    return {"message": "Password reset link sent to your email"}

@router.post("/forgot-password-verify")
def forgot_password_verify(body:ForgotPasswordVerifyDto):

    user = User.find_one({
        "email":body.email
    })

    if not user:
        raise HTTPException(status_code=404, detail="Email not found")
    
    verification = EmailVerification.find_one({"token": body.token, "is_used": False, "user_id": user.id})


    if not verification:
        raise HTTPException(status_code=400, detail="Invalid or expired verification token")

    expires_at = verification.expires_at
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)

    # Check if the token has expired
    if expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Verification token has expired")
    
    # Mark the token as used
    EmailVerification.update(verification.id, is_used=True)
    # Update the user's password

    User.update(user.id, password= hash_password(body.new_password))
    return {"message": "Password reset successfully"}



@router.get('/invitations')
def get_invitations(user=Depends(get_current_user)):
    return OrganizationInvitation.filter(where={
        "email":user.email
    })



@router.get("/oauth/google")
async def login(request: Request):
    redirect_uri = request.url_for('auth')

    return await oauth.google.authorize_redirect(request, redirect_uri)

@router.get("/oauth/google/callback")
async def auth(request: Request):

    response = await oauth.google.authorize_access_token(request)

    userinfo = response.get('userinfo')

    name = userinfo.get('email')
    email = userinfo.get('email')
    image = userinfo.get('picture')

    user = User.find_one(where={
        "email":email
    })
    
    if not user:
        user = User.create(email=email,name=name,image=image,email_verified_at=datetime.utcnow(),password='')
    
    tokens =  create_token(user)

    redirect_url = f"{settings.FRONTEND_URL}/login?access_token={tokens.get('access_token')}&refresh_token={tokens.get('refresh_token')}"

    return RedirectResponse(redirect_url)

