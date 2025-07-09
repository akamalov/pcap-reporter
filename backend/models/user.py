"""
User model for authentication and authorization.
"""

from beanie import Document, Indexed
from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from datetime import datetime
from passlib.context import CryptContext

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class User(Document):
    """
    MongoDB document model for users.
    """
    
    # Basic user information
    username: Indexed(str)  # Unique username
    email: Indexed(EmailStr)  # Unique email
    hashed_password: str
    
    # User status
    is_active: bool = True
    is_admin: bool = False
    
    # Timestamps
    created_at: Indexed(datetime) = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None
    
    # Profile information
    full_name: Optional[str] = None
    organization: Optional[str] = None
    
    # Permissions and preferences
    permissions: List[str] = Field(default_factory=list)
    preferences: dict = Field(default_factory=dict)
    
    class Settings:
        name = "users"
        indexes = [
            [("username", 1)],  # Unique index
            [("email", 1)],     # Unique index
            [("created_at", -1)],
            [("is_active", 1)],
        ]
    
    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash a password using bcrypt.
        """
        return pwd_context.hash(password)
    
    def verify_password(self, password: str) -> bool:
        """
        Verify a password against the stored hash.
        """
        return pwd_context.verify(password, self.hashed_password)
    
    def update_password(self, new_password: str):
        """
        Update user password with a new hashed password.
        """
        self.hashed_password = self.hash_password(new_password)
        self.updated_at = datetime.utcnow()
    
    def update_last_login(self):
        """
        Update the last login timestamp.
        """
        self.last_login = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def has_permission(self, permission: str) -> bool:
        """
        Check if user has a specific permission.
        """
        return self.is_admin or permission in self.permissions
    
    def add_permission(self, permission: str):
        """
        Add a permission to the user.
        """
        if permission not in self.permissions:
            self.permissions.append(permission)
            self.updated_at = datetime.utcnow()
    
    def remove_permission(self, permission: str):
        """
        Remove a permission from the user.
        """
        if permission in self.permissions:
            self.permissions.remove(permission)
            self.updated_at = datetime.utcnow()
    
    def to_dict(self, include_sensitive: bool = False) -> dict:
        """
        Convert user to dictionary for API responses.
        """
        user_dict = {
            "id": str(self.id),
            "username": self.username,
            "email": self.email,
            "is_active": self.is_active,
            "is_admin": self.is_admin,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "full_name": self.full_name,
            "organization": self.organization,
            "permissions": self.permissions,
        }
        
        if include_sensitive:
            user_dict["preferences"] = self.preferences
        
        return user_dict
    
    @classmethod
    async def create_user(
        cls,
        username: str,
        email: str,
        password: str,
        full_name: Optional[str] = None,
        is_admin: bool = False,
        organization: Optional[str] = None,
    ) -> "User":
        """
        Create a new user with hashed password.
        """
        user = cls(
            username=username,
            email=email,
            hashed_password=cls.hash_password(password),
            full_name=full_name,
            is_admin=is_admin,
            organization=organization,
        )
        await user.insert()
        return user
    
    @classmethod
    async def authenticate(cls, username: str, password: str) -> Optional["User"]:
        """
        Authenticate a user with username and password.
        """
        user = await cls.find_one({"username": username, "is_active": True})
        if user and user.verify_password(password):
            await user.update_last_login()
            await user.save()
            return user
        return None 