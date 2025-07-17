"""
Authentication service for JWT tokens and OAuth2 integration.
"""

import jwt
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from fastapi import HTTPException, status
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr

from models.user import User, UserRole, UserPermission
from models.organization import Organization
from core.config import get_settings

settings = get_settings()

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class TokenData(BaseModel):
    """
    Token data structure for JWT tokens.
    """
    user_id: str
    username: str
    email: str
    organization_id: Optional[str] = None
    role: UserRole
    permissions: List[str]
    is_admin: bool = False
    exp: datetime
    iat: datetime
    token_type: str = "access"


class RefreshTokenData(BaseModel):
    """
    Refresh token data structure.
    """
    user_id: str
    token_id: str
    exp: datetime
    iat: datetime
    token_type: str = "refresh"


class AuthService:
    """
    Authentication service for handling JWT tokens and user authentication.
    """
    
    def __init__(self):
        self.secret_key = settings.SECRET_KEY
        self.algorithm = "HS256"
        self.access_token_expire_minutes = 60  # 1 hour
        self.refresh_token_expire_days = 7  # 7 days
        
    def create_access_token(self, user: User) -> str:
        """
        Create a JWT access token for a user.
        """
        now = datetime.utcnow()
        expire = now + timedelta(minutes=self.access_token_expire_minutes)
        
        token_data = TokenData(
            user_id=str(user.id),
            username=user.username,
            email=user.email,
            organization_id=user.organization_id,
            role=user.role,
            permissions=[perm.value for perm in user.permissions],
            is_admin=user.is_admin,
            exp=expire,
            iat=now,
            token_type="access"
        )
        
        return jwt.encode(
            token_data.dict(),
            self.secret_key,
            algorithm=self.algorithm
        )
    
    def create_refresh_token(self, user: User) -> str:
        """
        Create a JWT refresh token for a user.
        """
        now = datetime.utcnow()
        expire = now + timedelta(days=self.refresh_token_expire_days)
        token_id = secrets.token_urlsafe(32)
        
        token_data = RefreshTokenData(
            user_id=str(user.id),
            token_id=token_id,
            exp=expire,
            iat=now,
            token_type="refresh"
        )
        
        return jwt.encode(
            token_data.dict(),
            self.secret_key,
            algorithm=self.algorithm
        )
    
    def verify_token(self, token: str) -> TokenData:
        """
        Verify and decode a JWT token.
        """
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm]
            )
            
            if payload.get("token_type") != "access":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token type"
                )
            
            return TokenData(**payload)
        
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
    
    def verify_refresh_token(self, token: str) -> RefreshTokenData:
        """
        Verify and decode a refresh token.
        """
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm]
            )
            
            if payload.get("token_type") != "refresh":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token type"
                )
            
            return RefreshTokenData(**payload)
        
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token has expired"
            )
        except jwt.JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
    
    async def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """
        Authenticate a user with username/email and password.
        """
        # Try to find user by username
        user = await User.find_one({"username": username, "is_active": True})
        
        # If not found, try by email
        if not user:
            user = await User.find_one({"email": username, "is_active": True})
        
        if not user:
            return None
        
        # Check if account is locked
        if user.is_account_locked():
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail="Account is temporarily locked due to failed login attempts"
            )
        
        # Verify password
        if not user.verify_password(password):
            user.increment_failed_login()
            await user.save()
            return None
        
        # Reset failed login attempts on successful login
        user.failed_login_attempts = 0
        await user.update_last_login()
        await user.save()
        
        return user
    
    async def get_current_user(self, token: str) -> User:
        """
        Get the current user from a JWT token.
        """
        token_data = self.verify_token(token)
        user = await User.get(token_data.user_id)
        
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )
        
        return user
    
    async def refresh_access_token(self, refresh_token: str) -> str:
        """
        Create a new access token using a refresh token.
        """
        token_data = self.verify_refresh_token(refresh_token)
        user = await User.get(token_data.user_id)
        
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )
        
        return self.create_access_token(user)
    
    async def register_user(
        self,
        username: str,
        email: str,
        password: str,
        full_name: Optional[str] = None,
        organization_id: Optional[str] = None,
        role: UserRole = UserRole.VIEWER
    ) -> User:
        """
        Register a new user.
        """
        # Check if username already exists
        existing_user = await User.find_one({"username": username})
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already exists"
            )
        
        # Check if email already exists
        existing_email = await User.find_one({"email": email})
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Validate password strength
        if not self.validate_password(password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password does not meet security requirements"
            )
        
        # Check organization limits if applicable
        if organization_id:
            organization = await Organization.get(organization_id)
            if not organization or not organization.can_create_user():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Organization cannot create new users"
                )
        
        # Create new user
        user = await User.create_user(
            username=username,
            email=email,
            password=password,
            full_name=full_name,
            organization_id=organization_id,
            role=role
        )
        
        # Update organization user count
        if organization_id:
            organization.increment_usage(users=1)
            await organization.save()
        
        return user
    
    def validate_password(self, password: str) -> bool:
        """
        Validate password strength.
        """
        if len(password) < 8:
            return False
        
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_symbol = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)
        
        return has_upper and has_lower and has_digit and has_symbol
    
    async def change_password(
        self,
        user: User,
        old_password: str,
        new_password: str
    ) -> bool:
        """
        Change user password.
        """
        if not user.verify_password(old_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )
        
        if not self.validate_password(new_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New password does not meet security requirements"
            )
        
        user.update_password(new_password)
        await user.save()
        
        return True
    
    async def reset_password(
        self,
        email: str,
        new_password: str,
        reset_token: str
    ) -> bool:
        """
        Reset user password using a reset token.
        """
        # In a real implementation, you would validate the reset token
        # For now, we'll implement a basic version
        user = await User.get_by_email(email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        if not self.validate_password(new_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New password does not meet security requirements"
            )
        
        user.update_password(new_password)
        user.unlock_account()  # Unlock account on password reset
        await user.save()
        
        return True
    
    async def check_permission(
        self,
        user: User,
        permission: UserPermission,
        organization_id: Optional[str] = None
    ) -> bool:
        """
        Check if user has a specific permission.
        """
        # Super admins have all permissions
        if user.is_admin or user.role == UserRole.SUPER_ADMIN:
            return True
        
        # Check organization membership if required
        if organization_id and user.organization_id != organization_id:
            return False
        
        return user.has_permission(permission)
    
    async def get_user_permissions(self, user: User) -> List[str]:
        """
        Get all permissions for a user.
        """
        if user.is_admin or user.role == UserRole.SUPER_ADMIN:
            return [perm.value for perm in UserPermission]
        
        # Get role-based permissions
        role_permissions = {
            UserRole.ORG_ADMIN: [
                UserPermission.ANALYZE_FILES,
                UserPermission.VIEW_ANALYSES,
                UserPermission.DELETE_ANALYSES,
                UserPermission.EXPORT_REPORTS,
                UserPermission.MANAGE_USERS,
                UserPermission.VIEW_USERS,
                UserPermission.INVITE_USERS,
                UserPermission.MANAGE_ORGANIZATION,
                UserPermission.VIEW_ORGANIZATION,
                UserPermission.MANAGE_BILLING,
            ],
            UserRole.ANALYST: [
                UserPermission.ANALYZE_FILES,
                UserPermission.VIEW_ANALYSES,
                UserPermission.EXPORT_REPORTS,
                UserPermission.VIEW_USERS,
            ],
            UserRole.VIEWER: [
                UserPermission.VIEW_ANALYSES,
                UserPermission.EXPORT_REPORTS,
            ],
            UserRole.GUEST: [
                UserPermission.VIEW_ANALYSES,
            ],
        }
        
        permissions = set()
        
        # Add role-based permissions
        for perm in role_permissions.get(user.role, []):
            permissions.add(perm.value)
        
        # Add explicit permissions
        for perm in user.permissions:
            permissions.add(perm.value)
        
        return list(permissions)


# Global auth service instance
auth_service = AuthService()