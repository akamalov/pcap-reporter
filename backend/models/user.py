"""
User model for authentication and authorization.
"""

from beanie import Document, Indexed
from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime
from passlib.context import CryptContext
from enum import Enum

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class UserRole(str, Enum):
    """
    User roles within an organization.
    """
    SUPER_ADMIN = "super_admin"  # System-wide admin
    ORG_ADMIN = "org_admin"      # Organization admin
    ANALYST = "analyst"          # Network analyst
    VIEWER = "viewer"            # Read-only access
    GUEST = "guest"              # Limited access


class UserPermission(str, Enum):
    """
    Granular permissions for users.
    """
    # Analysis permissions
    ANALYZE_FILES = "analyze_files"
    VIEW_ANALYSES = "view_analyses"
    DELETE_ANALYSES = "delete_analyses"
    EXPORT_REPORTS = "export_reports"
    
    # User management
    MANAGE_USERS = "manage_users"
    VIEW_USERS = "view_users"
    INVITE_USERS = "invite_users"
    
    # Organization management
    MANAGE_ORGANIZATION = "manage_organization"
    VIEW_ORGANIZATION = "view_organization"
    MANAGE_BILLING = "manage_billing"
    
    # System administration
    SYSTEM_ADMIN = "system_admin"
    VIEW_SYSTEM_LOGS = "view_system_logs"
    MANAGE_SYSTEM_SETTINGS = "manage_system_settings"


class UserPreferences(BaseModel):
    """
    User preferences and settings.
    """
    # UI preferences
    theme: str = "light"
    language: str = "en"
    timezone: str = "UTC"
    
    # Analysis preferences
    default_analysis_depth: str = "standard"
    auto_export_reports: bool = False
    notification_email: bool = True
    
    # Dashboard preferences
    dashboard_widgets: List[str] = Field(default_factory=lambda: [
        "recent_analyses", "system_health", "threat_summary"
    ])
    
    # Security preferences
    two_factor_enabled: bool = False
    session_timeout_minutes: int = 480  # 8 hours


class User(Document):
    """
    MongoDB document model for users.
    """
    
    # Basic user information
    username: Indexed(str, unique=True)  # Unique username
    email: Indexed(EmailStr, unique=True)  # Unique email
    hashed_password: str
    
    # Multi-tenant support
    organization_id: Optional[str] = None  # Reference to organization
    
    # User status and role
    is_active: bool = True
    is_admin: bool = False  # Global admin (super_admin)
    role: UserRole = UserRole.VIEWER
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None
    password_changed_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Profile information
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    job_title: Optional[str] = None
    department: Optional[str] = None
    
    # Contact information
    phone: Optional[str] = None
    
    # Security
    failed_login_attempts: int = 0
    account_locked_until: Optional[datetime] = None
    two_factor_secret: Optional[str] = None
    
    # Permissions and preferences
    permissions: List[UserPermission] = Field(default_factory=list)
    preferences: UserPreferences = Field(default_factory=UserPreferences)
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Settings:
        name = "users"
        indexes = [
            [("organization_id", 1)],
            [("created_at", -1)],
            [("is_active", 1)],
            [("role", 1)],
            [("last_login", -1)],
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
    
    def has_permission(self, permission: UserPermission) -> bool:
        """
        Check if user has a specific permission.
        """
        if self.is_admin or self.role == UserRole.SUPER_ADMIN:
            return True
        
        # Role-based permissions
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
        
        # Check role-based permissions
        if permission in role_permissions.get(self.role, []):
            return True
        
        # Check explicit permissions
        return permission in self.permissions
    
    def add_permission(self, permission: UserPermission):
        """
        Add a permission to the user.
        """
        if permission not in self.permissions:
            self.permissions.append(permission)
            self.updated_at = datetime.utcnow()
    
    def remove_permission(self, permission: UserPermission):
        """
        Remove a permission from the user.
        """
        if permission in self.permissions:
            self.permissions.remove(permission)
            self.updated_at = datetime.utcnow()
    
    def is_account_locked(self) -> bool:
        """
        Check if the account is locked due to failed login attempts.
        """
        if self.account_locked_until is None:
            return False
        return datetime.utcnow() < self.account_locked_until
    
    def lock_account(self, duration_minutes: int = 30):
        """
        Lock the account for a specified duration.
        """
        self.account_locked_until = datetime.utcnow().replace(
            minute=datetime.utcnow().minute + duration_minutes
        )
        self.updated_at = datetime.utcnow()
    
    def unlock_account(self):
        """
        Unlock the account and reset failed login attempts.
        """
        self.account_locked_until = None
        self.failed_login_attempts = 0
        self.updated_at = datetime.utcnow()
    
    def increment_failed_login(self):
        """
        Increment failed login attempts and lock if necessary.
        """
        self.failed_login_attempts += 1
        self.updated_at = datetime.utcnow()
        
        # Lock account after 5 failed attempts
        if self.failed_login_attempts >= 5:
            self.lock_account(30)  # Lock for 30 minutes
    
    def to_dict(self, include_sensitive: bool = False) -> dict:
        """
        Convert user to dictionary for API responses.
        """
        user_dict = {
            "id": str(self.id),
            "username": self.username,
            "email": self.email,
            "organization_id": self.organization_id,
            "is_active": self.is_active,
            "is_admin": self.is_admin,
            "role": self.role,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "full_name": self.full_name,
            "avatar_url": self.avatar_url,
            "job_title": self.job_title,
            "department": self.department,
            "phone": self.phone,
            "permissions": [perm.value for perm in self.permissions],
            "is_account_locked": self.is_account_locked(),
        }
        
        if include_sensitive:
            user_dict.update({
                "preferences": self.preferences.dict(),
                "failed_login_attempts": self.failed_login_attempts,
                "account_locked_until": self.account_locked_until.isoformat() if self.account_locked_until else None,
                "password_changed_at": self.password_changed_at.isoformat(),
                "two_factor_enabled": self.preferences.two_factor_enabled,
                "metadata": self.metadata,
            })
        
        return user_dict
    
    @classmethod
    async def create_user(
        cls,
        username: str,
        email: str,
        password: str,
        organization_id: Optional[str] = None,
        role: UserRole = UserRole.VIEWER,
        full_name: Optional[str] = None,
        is_admin: bool = False,
        **kwargs
    ) -> "User":
        """
        Create a new user with hashed password.
        """
        user = cls(
            username=username,
            email=email,
            hashed_password=cls.hash_password(password),
            organization_id=organization_id,
            role=role,
            full_name=full_name,
            is_admin=is_admin,
            **kwargs
        )
        await user.insert()
        return user
    
    @classmethod
    async def authenticate(cls, username: str, password: str) -> Optional["User"]:
        """
        Authenticate a user with username and password.
        """
        user = await cls.find_one({"username": username, "is_active": True})
        
        if not user:
            return None
        
        # Check if account is locked
        if user.is_account_locked():
            return None
        
        if user.verify_password(password):
            # Reset failed login attempts on successful login
            user.failed_login_attempts = 0
            await user.update_last_login()
            await user.save()
            return user
        else:
            # Increment failed login attempts
            user.increment_failed_login()
            await user.save()
            return None
    
    @classmethod
    async def get_by_organization(cls, organization_id: str) -> List["User"]:
        """
        Get all users belonging to an organization.
        """
        return await cls.find({"organization_id": organization_id, "is_active": True}).to_list()
    
    @classmethod
    async def get_by_email(cls, email: str) -> Optional["User"]:
        """
        Get user by email address.
        """
        return await cls.find_one({"email": email, "is_active": True})
    
    @classmethod
    async def get_organization_admins(cls, organization_id: str) -> List["User"]:
        """
        Get all organization admins for a specific organization.
        """
        return await cls.find({
            "organization_id": organization_id,
            "role": UserRole.ORG_ADMIN,
            "is_active": True
        }).to_list() 