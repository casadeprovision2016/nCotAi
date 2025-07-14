"""
Security utilities for JWT tokens, password hashing, MFA, etc.
"""

import base64
import io
import secrets
import string
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

import pyotp
import qrcode
from cryptography.fernet import Fernet
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ALGORITHM = "HS256"


def create_access_token(
    subject: Union[str, Any],
    expires_delta: Optional[timedelta] = None,
    additional_claims: Optional[Dict[str, Any]] = None,
) -> str:
    """Create JWT access token with optional additional claims."""
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "type": "access",
        "iat": datetime.utcnow(),
        "jti": secrets.token_urlsafe(16),  # JWT ID for token blacklisting
    }

    if additional_claims:
        to_encode.update(additional_claims)

    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(
    subject: Union[str, Any],
    expires_delta: Optional[timedelta] = None,
    device_info: Optional[Dict[str, Any]] = None,
) -> str:
    """Create JWT refresh token with device information."""
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES
        )

    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "type": "refresh",
        "iat": datetime.utcnow(),
        "jti": secrets.token_urlsafe(32),  # Longer JTI for refresh tokens
    }

    if device_info:
        to_encode["device"] = device_info

    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Generate password hash."""
    return pwd_context.hash(password)


def verify_token(token: str, token_type: str = "access") -> Optional[Dict[str, Any]]:
    """Verify JWT token and return payload."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != token_type:
            return None
        return payload
    except JWTError:
        return None


def extract_token_jti(token: str) -> Optional[str]:
    """Extract JWT ID from token without verification."""
    try:
        # Don't verify signature, just decode
        payload = jwt.get_unverified_claims(token)
        return payload.get("jti")
    except Exception:
        return None


def generate_verification_token() -> str:
    """Generate secure verification token."""
    return secrets.token_urlsafe(32)


def generate_reset_token() -> str:
    """Generate secure password reset token."""
    return secrets.token_urlsafe(32)


# MFA (Multi-Factor Authentication) functions
def generate_mfa_secret() -> str:
    """Generate a new TOTP secret for MFA."""
    return pyotp.random_base32()


def generate_qr_code_url(secret: str, user_email: str, issuer: str = "COTAI") -> str:
    """Generate QR code URL for TOTP setup."""
    totp = pyotp.TOTP(secret)
    provisioning_uri = totp.provisioning_uri(name=user_email, issuer_name=issuer)
    return provisioning_uri


def generate_qr_code_image(secret: str, user_email: str, issuer: str = "COTAI") -> str:
    """Generate QR code image as base64 string."""
    provisioning_uri = generate_qr_code_url(secret, user_email, issuer)

    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(provisioning_uri)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    # Convert to base64
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()

    return f"data:image/png;base64,{img_str}"


def verify_totp_code(secret: str, code: str, window: int = 1) -> bool:
    """Verify TOTP code with time window tolerance."""
    totp = pyotp.TOTP(secret)
    return totp.verify(code, valid_window=window)


def generate_backup_codes(count: int = 10) -> List[str]:
    """Generate backup codes for MFA recovery."""
    codes = []
    for _ in range(count):
        # Generate 8-character alphanumeric codes
        code = "".join(
            secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8)
        )
        # Add hyphen in the middle for readability
        formatted_code = f"{code[:4]}-{code[4:]}"
        codes.append(formatted_code)
    return codes


def hash_backup_codes(codes: List[str]) -> List[str]:
    """Hash backup codes for secure storage."""
    return [get_password_hash(code.replace("-", "").upper()) for code in codes]


def verify_backup_code(plain_code: str, hashed_codes: List[str]) -> bool:
    """Verify backup code against hashed codes."""
    normalized_code = plain_code.replace("-", "").upper()
    for hashed_code in hashed_codes:
        if verify_password(normalized_code, hashed_code):
            return True
    return False


# Encryption utilities for sensitive data
def get_encryption_key() -> bytes:
    """Get encryption key from settings."""
    # In production, this should be stored securely
    key = settings.SECRET_KEY.encode()[:32]  # Use first 32 bytes
    return base64.urlsafe_b64encode(key.ljust(32, b"0"))


def encrypt_data(data: str) -> str:
    """Encrypt sensitive data."""
    f = Fernet(get_encryption_key())
    encrypted_data = f.encrypt(data.encode())
    return base64.urlsafe_b64encode(encrypted_data).decode()


def decrypt_data(encrypted_data: str) -> str:
    """Decrypt sensitive data."""
    f = Fernet(get_encryption_key())
    decoded_data = base64.urlsafe_b64decode(encrypted_data.encode())
    decrypted_data = f.decrypt(decoded_data)
    return decrypted_data.decode()


# Password strength validation
def validate_password_strength(password: str) -> Dict[str, bool]:
    """Validate password strength and return detailed feedback."""
    validations = {
        "min_length": len(password) >= 8,
        "has_uppercase": any(c.isupper() for c in password),
        "has_lowercase": any(c.islower() for c in password),
        "has_digit": any(c.isdigit() for c in password),
        "has_special": any(c in '!@#$%^&*(),.?":{}|<>' for c in password),
        "no_common_patterns": not _has_common_patterns(password),
    }

    validations["is_strong"] = all(validations.values())
    return validations


def _has_common_patterns(password: str) -> bool:
    """Check for common weak password patterns."""
    password_lower = password.lower()

    # Common weak patterns
    weak_patterns = [
        "password",
        "123456",
        "qwerty",
        "admin",
        "root",
        "user",
        "guest",
        "welcome",
        "cotai",
        "system",
    ]

    for pattern in weak_patterns:
        if pattern in password_lower:
            return True

    # Sequential patterns
    if any(seq in password for seq in ["123", "abc", "321", "cba"]):
        return True

    # Repeated characters
    if any(password.count(char) > 2 for char in set(password)):
        return True

    return False


# Rate limiting utilities
def create_rate_limit_key(identifier: str, action: str) -> str:
    """Create Redis key for rate limiting."""
    return f"rate_limit:{action}:{identifier}"


def is_rate_limited(redis_client, key: str, limit: int, window: int) -> bool:
    """Check if action is rate limited."""
    try:
        current = redis_client.get(key)
        if current is None:
            redis_client.setex(key, window, 1)
            return False

        if int(current) >= limit:
            return True

        redis_client.incr(key)
        return False
    except Exception:
        # If Redis is down, don't block requests
        return False


# Device fingerprinting
def create_device_fingerprint(
    user_agent: str, ip_address: str, additional_info: Optional[Dict] = None
) -> str:
    """Create device fingerprint for security tracking."""
    import hashlib

    fingerprint_data = f"{user_agent}:{ip_address}"
    if additional_info:
        fingerprint_data += f":{str(additional_info)}"

    return hashlib.sha256(fingerprint_data.encode()).hexdigest()


def extract_device_info(user_agent: str) -> Dict[str, str]:
    """Extract device information from user agent."""
    # This is a simplified version. In production, use a library like user-agents
    device_info = {
        "user_agent": user_agent,
        "browser": "unknown",
        "os": "unknown",
        "device": "unknown",
    }

    if user_agent:
        ua_lower = user_agent.lower()

        # Browser detection
        if "chrome" in ua_lower:
            device_info["browser"] = "Chrome"
        elif "firefox" in ua_lower:
            device_info["browser"] = "Firefox"
        elif "safari" in ua_lower:
            device_info["browser"] = "Safari"
        elif "edge" in ua_lower:
            device_info["browser"] = "Edge"

        # OS detection
        if "windows" in ua_lower:
            device_info["os"] = "Windows"
        elif "macintosh" in ua_lower or "mac os" in ua_lower:
            device_info["os"] = "macOS"
        elif "linux" in ua_lower:
            device_info["os"] = "Linux"
        elif "android" in ua_lower:
            device_info["os"] = "Android"
        elif "ios" in ua_lower or "iphone" in ua_lower or "ipad" in ua_lower:
            device_info["os"] = "iOS"

        # Device type detection
        if "mobile" in ua_lower or "android" in ua_lower or "iphone" in ua_lower:
            device_info["device"] = "mobile"
        elif "tablet" in ua_lower or "ipad" in ua_lower:
            device_info["device"] = "tablet"
        else:
            device_info["device"] = "desktop"

    return device_info
