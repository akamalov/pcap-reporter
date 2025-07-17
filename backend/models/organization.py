"""
Organization model for multi-tenant architecture.
"""

from beanie import Document, Indexed
from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class OrganizationPlan(str, Enum):
    """
    Organization subscription plans.
    """
    FREE = "free"
    BASIC = "basic"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


class OrganizationSettings(BaseModel):
    """
    Organization-specific settings and configurations.
    """
    # Analysis settings
    max_concurrent_analyses: int = 5
    max_file_size_bytes: int = 2147483648  # 2GB
    retention_days: int = 30
    
    # Security settings
    require_2fa: bool = False
    password_policy: Dict[str, Any] = Field(default_factory=lambda: {
        "min_length": 8,
        "require_uppercase": True,
        "require_lowercase": True,
        "require_numbers": True,
        "require_symbols": True,
        "max_age_days": 90
    })
    
    # Feature flags
    advanced_analytics: bool = True
    ai_threat_detection: bool = True
    pdf_export: bool = True
    api_access: bool = True
    
    # Branding
    logo_url: Optional[str] = None
    primary_color: str = "#1890ff"
    organization_name: Optional[str] = None


class OrganizationUsage(BaseModel):
    """
    Organization usage metrics and limits.
    """
    # Current usage
    current_users: int = 0
    current_storage_bytes: int = 0
    analyses_this_month: int = 0
    
    # Limits
    max_users: int = 10
    max_storage_bytes: int = 107374182400  # 100GB
    max_analyses_per_month: int = 1000
    
    # Billing
    last_billing_date: Optional[datetime] = None
    next_billing_date: Optional[datetime] = None
    billing_email: Optional[EmailStr] = None


class Organization(Document):
    """
    MongoDB document model for organizations (multi-tenant).
    """
    
    # Basic organization information
    name: str  # Organization display name
    slug: str  # URL-friendly identifier (unique)
    description: Optional[str] = None
    
    # Contact information
    contact_email: EmailStr
    contact_phone: Optional[str] = None
    
    # Address information
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    
    # Subscription and plan
    plan: OrganizationPlan = OrganizationPlan.FREE
    plan_expires_at: Optional[datetime] = None
    
    # Organization status
    is_active: bool = True
    is_verified: bool = False
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Organization settings and usage
    settings: OrganizationSettings = Field(default_factory=OrganizationSettings)
    usage: OrganizationUsage = Field(default_factory=OrganizationUsage)
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Settings:
        name = "organizations"
        indexes = [
            [("slug", 1)],  # Unique index
            [("contact_email", 1)],
            [("created_at", -1)],
            [("is_active", 1)],
            [("plan", 1)],
        ]
    
    def is_plan_active(self) -> bool:
        """
        Check if the organization's plan is currently active.
        """
        if self.plan == OrganizationPlan.FREE:
            return True
        
        if self.plan_expires_at is None:
            return False
        
        return datetime.utcnow() < self.plan_expires_at
    
    def can_create_user(self) -> bool:
        """
        Check if the organization can create a new user.
        """
        if not self.is_active or not self.is_plan_active():
            return False
        
        return self.usage.current_users < self.usage.max_users
    
    def can_perform_analysis(self) -> bool:
        """
        Check if the organization can perform a new analysis.
        """
        if not self.is_active or not self.is_plan_active():
            return False
        
        return self.usage.analyses_this_month < self.usage.max_analyses_per_month
    
    def can_store_file(self, file_size_bytes: int) -> bool:
        """
        Check if the organization can store a file of given size.
        """
        if not self.is_active or not self.is_plan_active():
            return False
        
        # Check individual file size limit
        if file_size_bytes > self.settings.max_file_size_bytes:
            return False
        
        # Check total storage limit
        return (self.usage.current_storage_bytes + file_size_bytes) <= self.usage.max_storage_bytes
    
    def has_feature(self, feature: str) -> bool:
        """
        Check if the organization has access to a specific feature.
        """
        if not self.is_active or not self.is_plan_active():
            return False
        
        feature_map = {
            "advanced_analytics": self.settings.advanced_analytics,
            "ai_threat_detection": self.settings.ai_threat_detection,
            "pdf_export": self.settings.pdf_export,
            "api_access": self.settings.api_access,
        }
        
        return feature_map.get(feature, False)
    
    def increment_usage(self, **kwargs):
        """
        Increment usage metrics.
        """
        if "users" in kwargs:
            self.usage.current_users += kwargs["users"]
        if "storage_bytes" in kwargs:
            self.usage.current_storage_bytes += kwargs["storage_bytes"]
        if "analyses" in kwargs:
            self.usage.analyses_this_month += kwargs["analyses"]
        
        self.updated_at = datetime.utcnow()
    
    def reset_monthly_usage(self):
        """
        Reset monthly usage counters (called by billing cycle).
        """
        self.usage.analyses_this_month = 0
        self.usage.last_billing_date = datetime.utcnow()
        
        # Calculate next billing date (30 days from now)
        next_billing = datetime.utcnow().replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )
        if next_billing.month == 12:
            next_billing = next_billing.replace(year=next_billing.year + 1, month=1)
        else:
            next_billing = next_billing.replace(month=next_billing.month + 1)
        
        self.usage.next_billing_date = next_billing
        self.updated_at = datetime.utcnow()
    
    def to_dict(self, include_sensitive: bool = False) -> dict:
        """
        Convert organization to dictionary for API responses.
        """
        org_dict = {
            "id": str(self.id),
            "name": self.name,
            "slug": self.slug,
            "description": self.description,
            "contact_email": self.contact_email,
            "contact_phone": self.contact_phone,
            "plan": self.plan,
            "plan_expires_at": self.plan_expires_at.isoformat() if self.plan_expires_at else None,
            "is_active": self.is_active,
            "is_verified": self.is_verified,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
        
        if include_sensitive:
            org_dict.update({
                "address_line1": self.address_line1,
                "address_line2": self.address_line2,
                "city": self.city,
                "state": self.state,
                "postal_code": self.postal_code,
                "country": self.country,
                "settings": self.settings.dict(),
                "usage": self.usage.dict(),
                "metadata": self.metadata,
            })
        
        return org_dict
    
    @classmethod
    async def create_organization(
        cls,
        name: str,
        slug: str,
        contact_email: str,
        plan: OrganizationPlan = OrganizationPlan.FREE,
        **kwargs
    ) -> "Organization":
        """
        Create a new organization.
        """
        # Set plan-specific defaults
        settings = OrganizationSettings()
        usage = OrganizationUsage()
        
        if plan == OrganizationPlan.BASIC:
            usage.max_users = 25
            usage.max_storage_bytes = 536870912000  # 500GB
            usage.max_analyses_per_month = 5000
        elif plan == OrganizationPlan.PROFESSIONAL:
            usage.max_users = 100
            usage.max_storage_bytes = 1073741824000  # 1TB
            usage.max_analyses_per_month = 25000
            settings.require_2fa = True
        elif plan == OrganizationPlan.ENTERPRISE:
            usage.max_users = 1000
            usage.max_storage_bytes = 5368709120000  # 5TB
            usage.max_analyses_per_month = 100000
            settings.require_2fa = True
            settings.advanced_analytics = True
        
        organization = cls(
            name=name,
            slug=slug,
            contact_email=contact_email,
            plan=plan,
            settings=settings,
            usage=usage,
            **kwargs
        )
        
        await organization.insert()
        return organization
    
    @classmethod
    async def get_by_slug(cls, slug: str) -> Optional["Organization"]:
        """
        Get organization by slug.
        """
        return await cls.find_one({"slug": slug, "is_active": True})
    
    @classmethod
    async def get_by_user_email(cls, email: str) -> Optional["Organization"]:
        """
        Get organization by user email (for single-tenant scenarios).
        """
        return await cls.find_one({"contact_email": email, "is_active": True})