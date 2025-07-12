# Security Enhancements and Best Practices

## Overview
This document outlines comprehensive security improvements to ensure the PCAP Reporter application meets enterprise security standards and protects against common vulnerabilities.

## 🔒 AUTHENTICATION & AUTHORIZATION

### 1. JWT-Based Authentication System
**Priority**: High  
**Impact**: Secure user sessions and API access

```python
# backend/auth/jwt_auth.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
import secrets
from typing import Optional

class JWTAuthManager:
    def __init__(self, secret_key: str, algorithm: str = "HS256"):
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        self.security = HTTPBearer()
        
    def create_access_token(
        self, 
        data: dict, 
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create JWT access token"""
        
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(hours=24)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        
        return encoded_jwt
    
    def verify_token(self, token: str) -> dict:
        """Verify and decode JWT token"""
        
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            username: str = payload.get("sub")
            
            if username is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Could not validate credentials"
                )
            
            return payload
            
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials"
            )
    
    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt"""
        return self.pwd_context.hash(password)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash"""
        return self.pwd_context.verify(plain_password, hashed_password)

# User model with security
from pydantic import BaseModel, EmailStr, validator
import re

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    
    @validator('username')
    def username_alphanumeric(cls, v):
        if not re.match("^[a-zA-Z0-9_-]+$", v):
            raise ValueError('Username must be alphanumeric with - and _ allowed')
        if len(v) < 3 or len(v) > 20:
            raise ValueError('Username must be between 3 and 20 characters')
        return v
    
    @validator('password')
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        if not re.search(r"[A-Z]", v):
            raise ValueError('Password must contain uppercase letter')
        if not re.search(r"[a-z]", v):
            raise ValueError('Password must contain lowercase letter')
        if not re.search(r"\d", v):
            raise ValueError('Password must contain digit')
        if not re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?]", v):
            raise ValueError('Password must contain special character')
        return v

class User(BaseModel):
    id: str
    username: str
    email: str
    is_active: bool = True
    is_admin: bool = False
    created_at: datetime
    last_login: Optional[datetime] = None
    failed_login_attempts: int = 0
    locked_until: Optional[datetime] = None

# Authentication endpoints
@app.post("/api/auth/register")
async def register_user(user_data: UserCreate):
    """Register new user with security validation"""
    
    # Check if user exists
    existing_user = await get_user_by_username(user_data.username)
    if existing_user:
        raise HTTPException(400, "Username already registered")
    
    existing_email = await get_user_by_email(user_data.email)
    if existing_email:
        raise HTTPException(400, "Email already registered")
    
    # Create user with hashed password
    auth_manager = get_auth_manager()
    hashed_password = auth_manager.hash_password(user_data.password)
    
    user = User(
        id=str(uuid.uuid4()),
        username=user_data.username,
        email=user_data.email,
        hashed_password=hashed_password,
        created_at=datetime.utcnow()
    )
    
    await create_user(user)
    
    # Create access token
    access_token = auth_manager.create_access_token(
        data={"sub": user.username, "user_id": user.id}
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email
        }
    }

@app.post("/api/auth/login")
async def login_user(username: str, password: str):
    """Authenticate user with rate limiting"""
    
    # Check rate limiting
    await check_login_rate_limit(username)
    
    user = await get_user_by_username(username)
    if not user:
        await record_failed_login(username)
        raise HTTPException(401, "Invalid credentials")
    
    # Check account lockout
    if user.locked_until and user.locked_until > datetime.utcnow():
        raise HTTPException(423, "Account temporarily locked")
    
    auth_manager = get_auth_manager()
    if not auth_manager.verify_password(password, user.hashed_password):
        await record_failed_login(username)
        
        # Lock account after 5 failed attempts
        if user.failed_login_attempts >= 4:
            await lock_user_account(user.id, minutes=15)
        
        raise HTTPException(401, "Invalid credentials")
    
    # Reset failed attempts on successful login
    await reset_failed_login_attempts(user.id)
    await update_last_login(user.id)
    
    # Create access token
    access_token = auth_manager.create_access_token(
        data={"sub": user.username, "user_id": user.id}
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }

# Dependency for protected routes
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())
) -> User:
    """Get current authenticated user"""
    
    auth_manager = get_auth_manager()
    payload = auth_manager.verify_token(credentials.credentials)
    
    user = await get_user_by_id(payload["user_id"])
    if not user:
        raise HTTPException(401, "User not found")
    
    if not user.is_active:
        raise HTTPException(401, "Inactive user")
    
    return user

# Protected route example
@app.get("/api/reports/my-reports")
async def get_user_reports(current_user: User = Depends(get_current_user)):
    """Get reports for authenticated user"""
    
    reports = await get_reports_by_user_id(current_user.id)
    return reports
```

### 2. Role-Based Access Control (RBAC)
**Priority**: Medium  
**Impact**: Fine-grained permission control

```python
# backend/auth/rbac.py
from enum import Enum
from typing import List, Set
from functools import wraps

class Permission(Enum):
    READ_REPORTS = "read_reports"
    WRITE_REPORTS = "write_reports"
    DELETE_REPORTS = "delete_reports"
    MANAGE_USERS = "manage_users"
    ADMIN_ACCESS = "admin_access"
    EXPORT_DATA = "export_data"

class Role(Enum):
    VIEWER = "viewer"
    ANALYST = "analyst"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"

# Role-permission mapping
ROLE_PERMISSIONS = {
    Role.VIEWER: {
        Permission.READ_REPORTS
    },
    Role.ANALYST: {
        Permission.READ_REPORTS,
        Permission.WRITE_REPORTS,
        Permission.EXPORT_DATA
    },
    Role.ADMIN: {
        Permission.READ_REPORTS,
        Permission.WRITE_REPORTS,
        Permission.DELETE_REPORTS,
        Permission.MANAGE_USERS,
        Permission.EXPORT_DATA
    },
    Role.SUPER_ADMIN: {
        Permission.READ_REPORTS,
        Permission.WRITE_REPORTS,
        Permission.DELETE_REPORTS,
        Permission.MANAGE_USERS,
        Permission.ADMIN_ACCESS,
        Permission.EXPORT_DATA
    }
}

def require_permission(permission: Permission):
    """Decorator to require specific permission"""
    
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            current_user = kwargs.get('current_user')
            if not current_user:
                raise HTTPException(401, "Authentication required")
            
            user_permissions = get_user_permissions(current_user)
            if permission not in user_permissions:
                raise HTTPException(403, "Insufficient permissions")
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

def get_user_permissions(user: User) -> Set[Permission]:
    """Get all permissions for a user"""
    
    permissions = set()
    for role in user.roles:
        permissions.update(ROLE_PERMISSIONS.get(role, set()))
    
    return permissions

# Usage example
@app.delete("/api/reports/{report_id}")
@require_permission(Permission.DELETE_REPORTS)
async def delete_report(
    report_id: str,
    current_user: User = Depends(get_current_user)
):
    """Delete report (requires delete permission)"""
    
    # Additional ownership check
    report = await get_report_by_id(report_id)
    if not report:
        raise HTTPException(404, "Report not found")
    
    # Users can only delete their own reports unless admin
    if (report.user_id != current_user.id and 
        Permission.ADMIN_ACCESS not in get_user_permissions(current_user)):
        raise HTTPException(403, "Can only delete own reports")
    
    await delete_report_by_id(report_id)
    return {"message": "Report deleted successfully"}
```

---

## 🛡️ INPUT VALIDATION & SANITIZATION

### 3. Comprehensive File Validation
**Priority**: Critical  
**Impact**: Prevents malicious file uploads

```python
# backend/security/file_validation.py
import magic
import hashlib
import zipfile
import tarfile
from pathlib import Path
from typing import Tuple, Dict, Any

class SecureFileValidator:
    
    # Allowed MIME types
    ALLOWED_MIME_TYPES = {
        'application/vnd.tcpdump.pcap',
        'application/octet-stream',  # Some systems report PCAP as this
        'application/cap',
        'application/pcapng'
    }
    
    # Maximum file sizes (in bytes)
    MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024  # 2GB
    MAX_COMPRESSED_SIZE = 500 * 1024 * 1024  # 500MB for compressed
    
    # Known malicious signatures
    MALICIOUS_SIGNATURES = [
        b'\\x4d\\x5a',  # PE executable
        b'\\x7f\\x45\\x4c\\x46',  # ELF executable
        b'\\xca\\xfe\\xba\\xbe',  # Mach-O executable
        b'\\x50\\x4b\\x03\\x04',  # ZIP archive (potential zip bomb)
    ]
    
    def __init__(self):
        self.magic = magic.Magic(mime=True)
    
    async def validate_pcap_file(self, file: UploadFile) -> Tuple[bool, Dict[str, Any]]:
        """Comprehensive PCAP file validation"""
        
        validation_result = {
            'valid': False,
            'file_info': {},
            'security_checks': {},
            'errors': []
        }
        
        try:
            # Read file content for analysis
            content = await file.read()
            file.file.seek(0)  # Reset file pointer
            
            # 1. Size validation
            file_size = len(content)
            if file_size > self.MAX_FILE_SIZE:
                validation_result['errors'].append(
                    f"File too large: {file_size} bytes (max: {self.MAX_FILE_SIZE})"
                )
                return False, validation_result
            
            # 2. MIME type validation
            mime_type = self.magic.from_buffer(content)
            validation_result['file_info']['mime_type'] = mime_type
            
            if mime_type not in self.ALLOWED_MIME_TYPES:
                validation_result['errors'].append(f"Invalid MIME type: {mime_type}")
            
            # 3. File signature validation
            is_valid_pcap, pcap_info = self._validate_pcap_signature(content)
            validation_result['file_info'].update(pcap_info)
            
            if not is_valid_pcap:
                validation_result['errors'].append("Invalid PCAP file signature")
            
            # 4. Malicious content scan
            security_scan = self._scan_for_malicious_content(content)
            validation_result['security_checks'] = security_scan
            
            if security_scan['threats_found']:
                validation_result['errors'].extend(security_scan['threats'])
            
            # 5. Archive bomb detection
            if self._is_compressed_file(content):
                compression_check = self._check_compression_bomb(content)
                validation_result['security_checks']['compression'] = compression_check
                
                if compression_check['is_bomb']:
                    validation_result['errors'].append("Potential compression bomb detected")
            
            # 6. File name validation
            filename_check = self._validate_filename(file.filename)
            validation_result['file_info']['filename_safe'] = filename_check['safe']
            
            if not filename_check['safe']:
                validation_result['errors'].append(f"Unsafe filename: {filename_check['reason']}")
            
            # Overall validation result
            validation_result['valid'] = len(validation_result['errors']) == 0
            
            return validation_result['valid'], validation_result
            
        except Exception as e:
            validation_result['errors'].append(f"Validation error: {str(e)}")
            return False, validation_result
    
    def _validate_pcap_signature(self, content: bytes) -> Tuple[bool, Dict[str, Any]]:
        """Validate PCAP file magic bytes"""
        
        pcap_info = {
            'format': 'unknown',
            'byte_order': 'unknown',
            'version': 'unknown'
        }
        
        if len(content) < 24:  # Minimum PCAP header size
            return False, pcap_info
        
        # Check PCAP magic numbers
        magic_bytes = content[:4]
        
        if magic_bytes == b'\\xa1\\xb2\\xc3\\xd4':
            pcap_info.update({
                'format': 'pcap',
                'byte_order': 'native',
                'version': f"{content[4]}.{content[5]}"
            })
            return True, pcap_info
        
        elif magic_bytes == b'\\xd4\\xc3\\xb2\\xa1':
            pcap_info.update({
                'format': 'pcap',
                'byte_order': 'swapped',
                'version': f"{content[5]}.{content[4]}"
            })
            return True, pcap_info
        
        elif magic_bytes == b'\\x0a\\x0d\\x0d\\x0a':
            pcap_info.update({
                'format': 'pcapng',
                'byte_order': 'native'
            })
            return True, pcap_info
        
        return False, pcap_info
    
    def _scan_for_malicious_content(self, content: bytes) -> Dict[str, Any]:
        """Scan for malicious content patterns"""
        
        security_scan = {
            'threats_found': False,
            'threats': [],
            'suspicious_patterns': []
        }
        
        # Check for malicious signatures
        for i, signature in enumerate(self.MALICIOUS_SIGNATURES):
            if signature in content:
                security_scan['threats_found'] = True
                security_scan['threats'].append(
                    f"Malicious signature {i+1} detected"
                )
        
        # Check for embedded executables
        if b'This program cannot be run in DOS mode' in content:
            security_scan['threats_found'] = True
            security_scan['threats'].append("Embedded Windows executable detected")
        
        # Check for suspicious URLs
        url_patterns = [b'http://', b'https://', b'ftp://']
        for pattern in url_patterns:
            if pattern in content:
                security_scan['suspicious_patterns'].append(
                    f"URL pattern detected: {pattern.decode()}"
                )
        
        return security_scan
    
    def _is_compressed_file(self, content: bytes) -> bool:
        """Check if file is compressed"""
        
        # ZIP signature
        if content.startswith(b'PK'):
            return True
        
        # GZIP signature
        if content.startswith(b'\\x1f\\x8b'):
            return True
        
        # TAR/GZIP signature
        if b'ustar' in content[257:262]:
            return True
        
        return False
    
    def _check_compression_bomb(self, content: bytes) -> Dict[str, Any]:
        """Check for compression bomb attacks"""
        
        compression_info = {
            'is_bomb': False,
            'compression_ratio': 0,
            'uncompressed_size': 0
        }
        
        try:
            # For ZIP files
            if content.startswith(b'PK'):
                import io
                zip_buffer = io.BytesIO(content)
                
                with zipfile.ZipFile(zip_buffer, 'r') as zip_file:
                    total_uncompressed = sum(
                        file_info.file_size for file_info in zip_file.filelist
                    )
                    
                    compression_info['uncompressed_size'] = total_uncompressed
                    compression_info['compression_ratio'] = total_uncompressed / len(content)
                    
                    # Compression bomb if ratio > 100:1 or uncompressed > 1GB
                    if (compression_info['compression_ratio'] > 100 or 
                        total_uncompressed > 1024 * 1024 * 1024):
                        compression_info['is_bomb'] = True
            
        except Exception:
            # If we can't analyze, err on the side of caution
            compression_info['is_bomb'] = True
        
        return compression_info
    
    def _validate_filename(self, filename: str) -> Dict[str, Any]:
        """Validate filename for security"""
        
        if not filename:
            return {'safe': False, 'reason': 'Empty filename'}
        
        # Check for path traversal
        if '..' in filename or '/' in filename or '\\' in filename:
            return {'safe': False, 'reason': 'Path traversal detected'}
        
        # Check for dangerous extensions
        dangerous_extensions = ['.exe', '.bat', '.cmd', '.scr', '.pif', '.com']
        for ext in dangerous_extensions:
            if filename.lower().endswith(ext):
                return {'safe': False, 'reason': f'Dangerous extension: {ext}'}
        
        # Check filename length
        if len(filename) > 255:
            return {'safe': False, 'reason': 'Filename too long'}
        
        # Check for control characters
        if any(ord(c) < 32 for c in filename):
            return {'safe': False, 'reason': 'Control characters in filename'}
        
        return {'safe': True, 'reason': 'Filename is safe'}

# Usage in upload endpoint
@app.post("/api/reports/upload")
async def secure_upload(
    file: UploadFile,
    current_user: User = Depends(get_current_user)
):
    """Secure file upload with comprehensive validation"""
    
    validator = SecureFileValidator()
    
    # Validate file
    is_valid, validation_result = await validator.validate_pcap_file(file)
    
    if not is_valid:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "File validation failed",
                "errors": validation_result['errors'],
                "file_info": validation_result['file_info']
            }
        )
    
    # Generate secure filename
    secure_filename = generate_secure_filename(file.filename)
    file_path = f"uploads/{current_user.id}/{secure_filename}"
    
    # Save file securely
    await save_file_securely(file, file_path)
    
    # Queue analysis
    job_id = str(uuid.uuid4())
    analyze_pcap_with_progress.delay(file_path, job_id)
    
    return {
        "job_id": job_id,
        "filename": secure_filename,
        "validation_result": validation_result
    }
```

### 4. API Input Sanitization
**Priority**: High  
**Impact**: Prevents injection attacks

```python
# backend/security/input_sanitization.py
import re
import html
import bleach
from typing import Any, Dict, List
from pydantic import BaseModel, validator

class InputSanitizer:
    
    # SQL injection patterns
    SQL_INJECTION_PATTERNS = [
        r"(\%27)|(\')|(\-\-)|(\%23)|(#)",
        r"((\%3D)|(=))[^\n]*((\%27)|(\')|(\-\-)|(\%23)|(#))",
        r"w*((\%27)|(\')|(\-\-)|(\%23)|(#))",
        r"((\%27)|(\')|(\-\-)|(\%23)|(#)).*?(((\%3D)|(=)).*?)",
        r"union.*select",
        r"select.*from",
        r"insert.*into",
        r"delete.*from",
        r"drop.*table"
    ]
    
    # XSS patterns
    XSS_PATTERNS = [
        r"<script[^>]*>.*?</script>",
        r"javascript:",
        r"on\w+\s*=",
        r"<iframe[^>]*>.*?</iframe>",
        r"<object[^>]*>.*?</object>",
        r"<embed[^>]*>.*?</embed>"
    ]
    
    @classmethod
    def sanitize_string(cls, value: str, max_length: int = None) -> str:
        """Sanitize string input"""
        
        if not isinstance(value, str):
            return str(value)
        
        # Remove null bytes
        value = value.replace('\\x00', '')
        
        # HTML encode
        value = html.escape(value)
        
        # Remove potential XSS
        for pattern in cls.XSS_PATTERNS:
            value = re.sub(pattern, '', value, flags=re.IGNORECASE)
        
        # Truncate if needed
        if max_length and len(value) > max_length:
            value = value[:max_length]
        
        return value.strip()
    
    @classmethod
    def detect_sql_injection(cls, value: str) -> bool:
        """Detect potential SQL injection"""
        
        value_lower = value.lower()
        
        for pattern in cls.SQL_INJECTION_PATTERNS:
            if re.search(pattern, value_lower, re.IGNORECASE):
                return True
        
        return False
    
    @classmethod
    def sanitize_dict(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively sanitize dictionary"""
        
        sanitized = {}
        
        for key, value in data.items():
            # Sanitize key
            clean_key = cls.sanitize_string(key, max_length=100)
            
            # Sanitize value based on type
            if isinstance(value, str):
                sanitized[clean_key] = cls.sanitize_string(value, max_length=10000)
            elif isinstance(value, dict):
                sanitized[clean_key] = cls.sanitize_dict(value)
            elif isinstance(value, list):
                sanitized[clean_key] = [
                    cls.sanitize_string(item) if isinstance(item, str) else item
                    for item in value
                ]
            else:
                sanitized[clean_key] = value
        
        return sanitized

# Secure Pydantic models
class SecureSearchRequest(BaseModel):
    query: str
    filters: Dict[str, Any] = {}
    page: int = 1
    page_size: int = 20
    
    @validator('query')
    def validate_query(cls, v):
        # Check for SQL injection
        if InputSanitizer.detect_sql_injection(v):
            raise ValueError('Potential SQL injection detected')
        
        # Sanitize and limit length
        sanitized = InputSanitizer.sanitize_string(v, max_length=500)
        
        if len(sanitized.strip()) == 0:
            raise ValueError('Search query cannot be empty')
        
        return sanitized
    
    @validator('filters')
    def validate_filters(cls, v):
        return InputSanitizer.sanitize_dict(v)
    
    @validator('page')
    def validate_page(cls, v):
        if v < 1 or v > 10000:
            raise ValueError('Page must be between 1 and 10000')
        return v
    
    @validator('page_size')
    def validate_page_size(cls, v):
        if v < 1 or v > 100:
            raise ValueError('Page size must be between 1 and 100')
        return v

# Middleware for automatic sanitization
from fastapi import Request
import json

@app.middleware("http")
async def sanitize_request_middleware(request: Request, call_next):
    """Middleware to sanitize all incoming requests"""
    
    # Skip for file uploads
    if request.headers.get("content-type", "").startswith("multipart/form-data"):
        response = await call_next(request)
        return response
    
    # Read and sanitize JSON body
    if request.headers.get("content-type") == "application/json":
        try:
            body = await request.body()
            if body:
                data = json.loads(body.decode())
                sanitized_data = InputSanitizer.sanitize_dict(data)
                
                # Replace request body with sanitized version
                request._body = json.dumps(sanitized_data).encode()
        except Exception:
            # If sanitization fails, continue with original request
            pass
    
    response = await call_next(request)
    return response
```

---

## 🌐 NETWORK SECURITY

### 5. Rate Limiting and DDoS Protection
**Priority**: High  
**Impact**: Prevents abuse and ensures availability

```python
# backend/security/rate_limiting.py
from fastapi import HTTPException, Request
from functools import wraps
import asyncio
import time
from typing import Dict, List
import redis.asyncio as redis

class RateLimiter:
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        
    async def is_rate_limited(
        self, 
        key: str, 
        limit: int, 
        window: int
    ) -> tuple[bool, Dict[str, Any]]:
        """Check if request should be rate limited"""
        
        current_time = int(time.time())
        pipeline = self.redis.pipeline()
        
        # Sliding window rate limiting
        window_start = current_time - window
        
        # Remove old entries
        pipeline.zremrangebyscore(key, 0, window_start)
        
        # Count current requests
        pipeline.zcard(key)
        
        # Add current request
        pipeline.zadd(key, {str(current_time): current_time})
        
        # Set expiry
        pipeline.expire(key, window)
        
        results = await pipeline.execute()
        request_count = results[1]
        
        rate_limit_info = {
            "limit": limit,
            "remaining": max(0, limit - request_count - 1),
            "reset_time": current_time + window,
            "window": window
        }
        
        return request_count >= limit, rate_limit_info

def rate_limit(requests_per_minute: int = 60, per_user: bool = True):
    """Rate limiting decorator"""
    
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request: Request = kwargs.get('request') or args[0]
            
            # Generate rate limit key
            if per_user and hasattr(request.state, 'user'):
                key = f"rate_limit:user:{request.state.user.id}"
            else:
                # Use IP address
                client_ip = request.client.host
                key = f"rate_limit:ip:{client_ip}"
            
            rate_limiter = get_rate_limiter()
            is_limited, info = await rate_limiter.is_rate_limited(
                key, requests_per_minute, 60
            )
            
            if is_limited:
                raise HTTPException(
                    status_code=429,
                    detail="Rate limit exceeded",
                    headers={
                        "X-RateLimit-Limit": str(info["limit"]),
                        "X-RateLimit-Remaining": str(info["remaining"]),
                        "X-RateLimit-Reset": str(info["reset_time"]),
                        "Retry-After": str(info["window"])
                    }
                )
            
            # Add rate limit headers to response
            response = await func(*args, **kwargs)
            
            if hasattr(response, 'headers'):
                response.headers["X-RateLimit-Limit"] = str(info["limit"])
                response.headers["X-RateLimit-Remaining"] = str(info["remaining"])
                response.headers["X-RateLimit-Reset"] = str(info["reset_time"])
            
            return response
        
        return wrapper
    return decorator

# Usage examples
@app.post("/api/auth/login")
@rate_limit(requests_per_minute=5, per_user=False)  # 5 login attempts per IP
async def login(request: Request, credentials: UserLogin):
    pass

@app.post("/api/reports/upload")
@rate_limit(requests_per_minute=10, per_user=True)  # 10 uploads per user
async def upload_file(request: Request, file: UploadFile):
    pass

# DDoS protection middleware
@app.middleware("http")
async def ddos_protection_middleware(request: Request, call_next):
    """Basic DDoS protection"""
    
    client_ip = request.client.host
    
    # Check for suspicious patterns
    suspicious_indicators = [
        len(request.url.path) > 2000,  # Extremely long URLs
        request.headers.get("user-agent", "").lower() in ["", "curl", "wget"],  # Suspicious user agents
        "." * 50 in str(request.url),  # Repetitive patterns
    ]
    
    if any(suspicious_indicators):
        # Log suspicious activity
        logger.warning(f"Suspicious request from {client_ip}: {request.url}")
        
        # Implement temporary block
        await block_ip_temporarily(client_ip, minutes=5)
        
        raise HTTPException(
            status_code=403,
            detail="Request blocked by security policy"
        )
    
    response = await call_next(request)
    return response
```

### 6. HTTPS and Security Headers
**Priority**: High  
**Impact**: Secure communication and browser security

```python
# backend/security/headers.py
from fastapi import FastAPI
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from starlette.middleware.sessions import SessionMiddleware
import secrets

def setup_security_middleware(app: FastAPI):
    """Configure security middleware and headers"""
    
    # HTTPS redirect (only in production)
    if settings.ENVIRONMENT == "production":
        app.add_middleware(HTTPSRedirectMiddleware)
    
    # Trusted hosts
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.ALLOWED_HOSTS
    )
    
    # Secure sessions
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.SESSION_SECRET_KEY,
        https_only=settings.ENVIRONMENT == "production",
        same_site="strict"
    )

@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    """Add security headers to all responses"""
    
    response = await call_next(request)
    
    # Security headers
    security_headers = {
        # Prevent MIME type sniffing
        "X-Content-Type-Options": "nosniff",
        
        # XSS Protection
        "X-XSS-Protection": "1; mode=block",
        
        # Frame options (prevent clickjacking)
        "X-Frame-Options": "DENY",
        
        # HSTS (force HTTPS)
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
        
        # CSP (Content Security Policy)
        "Content-Security-Policy": (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://unpkg.com; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data: https:; "
            "connect-src 'self' ws: wss:; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        ),
        
        # Referrer Policy
        "Referrer-Policy": "strict-origin-when-cross-origin",
        
        # Permissions Policy
        "Permissions-Policy": (
            "camera=(), microphone=(), geolocation=(), "
            "accelerometer=(), gyroscope=(), magnetometer=(), "
            "payment=(), usb=()"
        )
    }
    
    # Add all security headers
    for header, value in security_headers.items():
        response.headers[header] = value
    
    return response

# SSL/TLS Configuration (nginx.conf)
SSL_CONFIG = """
# SSL Configuration
ssl_protocols TLSv1.2 TLSv1.3;
ssl_ciphers ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-RSA-AES128-SHA256:ECDHE-RSA-AES256-SHA384;
ssl_prefer_server_ciphers off;

# SSL Security
ssl_session_cache shared:SSL:10m;
ssl_session_timeout 10m;
ssl_session_tickets off;

# OCSP Stapling
ssl_stapling on;
ssl_stapling_verify on;

# Security Headers
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
add_header X-Frame-Options DENY always;
add_header X-Content-Type-Options nosniff always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
"""
```

---

## 📊 AUDIT & MONITORING

### 7. Security Audit Logging
**Priority**: Medium  
**Impact**: Comprehensive security monitoring

```python
# backend/security/audit_logging.py
import logging
import json
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional

class AuditEventType(Enum):
    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    USER_CREATED = "user_created"
    FILE_UPLOAD = "file_upload"
    FILE_DOWNLOAD = "file_download"
    ANALYSIS_STARTED = "analysis_started"
    ANALYSIS_COMPLETED = "analysis_completed"
    SECURITY_VIOLATION = "security_violation"
    ADMIN_ACTION = "admin_action"
    PERMISSION_DENIED = "permission_denied"

class SecurityAuditor:
    def __init__(self):
        self.logger = logging.getLogger("security_audit")
        
        # Configure audit logger
        handler = logging.FileHandler("logs/security_audit.log")
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
    
    async def log_event(
        self,
        event_type: AuditEventType,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        details: Dict[str, Any] = None,
        severity: str = "info"
    ):
        """Log security audit event"""
        
        audit_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type.value,
            "user_id": user_id,
            "ip_address": ip_address,
            "severity": severity,
            "details": details or {}
        }
        
        # Log to file
        log_message = json.dumps(audit_record)
        
        if severity == "critical":
            self.logger.critical(log_message)
        elif severity == "warning":
            self.logger.warning(log_message)
        else:
            self.logger.info(log_message)
        
        # Store in database for analysis
        await self.store_audit_record(audit_record)
        
        # Send alerts for critical events
        if severity == "critical":
            await self.send_security_alert(audit_record)
    
    async def store_audit_record(self, record: Dict[str, Any]):
        """Store audit record in database"""
        
        db = get_database()
        await db.security_audit.insert_one(record)
    
    async def send_security_alert(self, record: Dict[str, Any]):
        """Send security alert for critical events"""
        
        # Implementation depends on notification system
        # Could send email, Slack message, webhook, etc.
        pass

# Usage in endpoints
@app.post("/api/auth/login")
async def login(request: Request, credentials: UserLogin):
    auditor = SecurityAuditor()
    
    try:
        # Attempt login
        user = await authenticate_user(credentials)
        
        await auditor.log_event(
            AuditEventType.USER_LOGIN,
            user_id=user.id,
            ip_address=request.client.host,
            details={
                "username": credentials.username,
                "success": True,
                "user_agent": request.headers.get("user-agent")
            }
        )
        
        return {"access_token": "..."}
        
    except HTTPException as e:
        await auditor.log_event(
            AuditEventType.USER_LOGIN,
            ip_address=request.client.host,
            details={
                "username": credentials.username,
                "success": False,
                "error": str(e.detail),
                "user_agent": request.headers.get("user-agent")
            },
            severity="warning"
        )
        raise

# Security monitoring dashboard endpoint
@app.get("/api/admin/security/events")
@require_permission(Permission.ADMIN_ACCESS)
async def get_security_events(
    event_type: Optional[str] = None,
    severity: Optional[str] = None,
    hours: int = 24,
    current_user: User = Depends(get_current_user)
):
    """Get security audit events for monitoring"""
    
    db = get_database()
    
    # Build query
    query = {
        "timestamp": {
            "$gte": datetime.utcnow() - timedelta(hours=hours)
        }
    }
    
    if event_type:
        query["event_type"] = event_type
    
    if severity:
        query["severity"] = severity
    
    # Get events
    events = await db.security_audit.find(query).sort("timestamp", -1).to_list(100)
    
    # Aggregate statistics
    stats = await db.security_audit.aggregate([
        {"$match": query},
        {"$group": {
            "_id": "$event_type",
            "count": {"$sum": 1}
        }}
    ]).to_list(None)
    
    return {
        "events": events,
        "statistics": stats,
        "query_period_hours": hours
    }
```

---

## 📋 Implementation Priority

### Phase 1: Critical Security (Week 1-2)
1. Implement JWT authentication system
2. Add comprehensive file validation
3. Configure HTTPS and security headers
4. Set up rate limiting

### Phase 2: Access Control (Week 3)
1. Implement RBAC system
2. Add input sanitization
3. Set up audit logging
4. Configure DDoS protection

### Phase 3: Monitoring (Week 4)
1. Security monitoring dashboard
2. Alert systems
3. Penetration testing
4. Security documentation