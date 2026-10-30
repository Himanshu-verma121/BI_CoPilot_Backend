from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from datetime import datetime
from database.db import get_db
from models.models import User, Company
from utils.auth import hash_password, verify_password, create_token, verify_token

router = APIRouter(prefix="/auth", tags=["Authentication"])


class RegisterRequest(BaseModel):
    company_name : str
    name         : str
    email        : EmailStr   
    password     : str

class LoginRequest(BaseModel):
    email    : EmailStr
    password : str


# Register
@router.post("/register")
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    
    existing = db.query(User).filter(User.email == data.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    company = Company(
        name  = data.company_name,
        email = data.email,
    )
    db.add(company)
    db.flush()  

    # Admin user for this company
    user = User(
        company_id    = company.id,
        name          = data.name,
        email         = data.email,
        password_hash = hash_password(data.password),
        role          = "admin"   # first user = admin
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_token(
        user_id    = user.id,
        company_id = company.id,
        email      = user.email
    )

    return {
        "message"    : "Registration successful!",
        "token"      : token,
        "user": {
            "id"          : user.id,
            "name"        : user.name,
            "email"       : user.email,
            "role"        : user.role,
            "company_id"  : company.id,
            "company_name": company.name
        }
    }


# Login 
@router.post("/login")
def login(data: LoginRequest, db: Session = Depends(get_db)):

    user = db.query(User).filter(User.email == data.email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    # Verify password
    if not verify_password(data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated. Contact admin."
        )

    # Update  login
    user.last_login = datetime.utcnow()
    db.commit()

    token = create_token(
        user_id    = user.id,
        company_id = user.company_id,
        email      = user.email
    )

    return {
        "message": "Login successful!",
        "token"  : token,
        "user"   : {
            "id"        : user.id,
            "name"      : user.name,
            "email"     : user.email,
            "role"      : user.role,
            "company_id": user.company_id,
        }
    }


# Get Current User 
@router.get("/me")
def get_me(
    db           : Session = Depends(get_db),
    current_user : dict    = Depends(verify_token)
):
   
    user = db.query(User).filter(
        User.id == current_user["user_id"]
    ).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "id"          : user.id,
        "name"        : user.name,
        "email"       : user.email,
        "role"        : user.role,
        "company_id"  : user.company_id,
        "last_login"  : user.last_login
    }