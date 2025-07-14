"""
Security Middleware for COTAI application
Handles security headers, rate limiting, and request validation
"""

import logging
import time
from typing import Any, Callable, Dict, Optional

import redis
from fastapi import HTTPException, Request, Response, status
from fastapi.security.utils import get_authorization_scheme_param
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core.config import settings
from app.core.security import create_rate_limit_key, is_rate_limited

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers to all responses."""

    def __init__(self, app, environment: str = "production"):
        super().__init__(app)
        self.environment = environment

        # Security headers configuration
        self.security_headers = {
            # Prevent clickjacking
            "X-Frame-Options": "DENY",
            # Prevent content type sniffing
            "X-Content-Type-Options": "nosniff",
            # XSS protection
            "X-XSS-Protection": "1; mode=block",
            # Referrer policy
            "Referrer-Policy": "strict-origin-when-cross-origin",
            # Permissions policy (replace Feature-Policy)
            "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
            # Remove server information
            "Server": "COTAI/2.0",
        }

        # HSTS header for HTTPS
        if environment == "production":
            self.security_headers[
                "Strict-Transport-Security"
            ] = "max-age=31536000; includeSubDomains; preload"

        # Content Security Policy
        self.csp_policy = self._build_csp_policy()

    def _build_csp_policy(self) -> str:
        """Build Content Security Policy."""

        if self.environment == "development":
            # More relaxed CSP for development
            return (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval' localhost:* 127.0.0.1:*; "
                "style-src 'self' 'unsafe-inline' fonts.googleapis.com; "
                "font-src 'self' fonts.gstatic.com; "
                "img-src 'self' data: blob: https:; "
                "connect-src 'self' localhost:* 127.0.0.1:* ws: wss:; "
                "media-src 'self'; "
                "object-src 'none'; "
                "base-uri 'self'; "
                "frame-ancestors 'none';"
            )
        else:
            # Strict CSP for production
            return (
                "default-src 'self'; "
                "script-src 'self'; "
                "style-src 'self' 'unsafe-inline' fonts.googleapis.com; "
                "font-src 'self' fonts.gstatic.com; "
                "img-src 'self' data: blob:; "
                "connect-src 'self' wss:; "
                "media-src 'self'; "
                "object-src 'none'; "
                "base-uri 'self'; "
                "frame-ancestors 'none'; "
                "upgrade-insecure-requests;"
            )

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and add security headers to response."""

        # Process request
        response = await call_next(request)

        # Add security headers
        for header, value in self.security_headers.items():
            response.headers[header] = value

        # Add CSP header
        response.headers["Content-Security-Policy"] = self.csp_policy

        return response


class RateLimitingMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware with Redis backend."""

    def __init__(self, app, redis_client=None):
        super().__init__(app)
        self.redis_client = redis_client

        # Rate limiting rules
        self.rate_limits = {
            # Authentication endpoints
            "/api/v1/auth/login": {
                "limit": 5,
                "window": 300,
            },  # 5 attempts per 5 minutes
            "/api/v1/auth/register": {
                "limit": 3,
                "window": 3600,
            },  # 3 attempts per hour
            "/api/v1/auth/password-reset": {"limit": 3, "window": 3600},
            # MFA endpoints
            "/api/v1/mfa/verify": {
                "limit": 10,
                "window": 300,
            },  # 10 attempts per 5 minutes
            "/api/v1/mfa/setup": {"limit": 3, "window": 3600},
            # API endpoints (general)
            "default": {"limit": 100, "window": 60},  # 100 requests per minute
            # File uploads
            "/api/v1/files/upload": {
                "limit": 10,
                "window": 300,
            },  # 10 uploads per 5 minutes
        }

    def _get_client_identifier(self, request: Request) -> str:
        """Get unique identifier for client (IP + User if available)."""

        # Get IP address
        ip = request.client.host if request.client else "unknown"
        x_forwarded_for = request.headers.get("X-Forwarded-For")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0].strip()

        # Try to get user from token (if available)
        user_id = None
        authorization = request.headers.get("Authorization")
        if authorization:
            scheme, token = get_authorization_scheme_param(authorization)
            if scheme.lower() == "bearer" and token:
                try:
                    from app.core.security import verify_token

                    payload = verify_token(token)
                    if payload:
                        user_id = payload.get("sub")
                except:
                    pass

        # Create identifier
        identifier = f"{ip}"
        if user_id:
            identifier += f":{user_id}"

        return identifier

    def _get_rate_limit_for_path(self, path: str) -> Dict[str, int]:
        """Get rate limit configuration for specific path."""

        # Check exact matches first
        if path in self.rate_limits:
            return self.rate_limits[path]

        # Check prefix matches
        for pattern, config in self.rate_limits.items():
            if pattern != "default" and path.startswith(pattern):
                return config

        # Return default
        return self.rate_limits["default"]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Check rate limits before processing request."""

        if not self.redis_client:
            # No Redis, skip rate limiting
            return await call_next(request)

        # Skip rate limiting for health checks
        if request.url.path.endswith("/health"):
            return await call_next(request)

        # Get rate limit configuration
        rate_config = self._get_rate_limit_for_path(request.url.path)
        limit = rate_config["limit"]
        window = rate_config["window"]

        # Get client identifier
        client_id = self._get_client_identifier(request)

        # Create rate limit key
        action = f"{request.method}:{request.url.path}"
        rate_key = create_rate_limit_key(client_id, action)

        # Check rate limit
        if is_rate_limited(self.redis_client, rate_key, limit, window):
            logger.warning(f"Rate limit exceeded for {client_id} on {action}")

            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": "Taxa de requisições excedida. Tente novamente mais tarde.",
                    "retry_after": window,
                },
                headers={
                    "Retry-After": str(window),
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Window": str(window),
                },
            )

        # Process request
        response = await call_next(request)

        # Add rate limit headers to response
        try:
            current_count = self.redis_client.get(rate_key)
            if current_count:
                remaining = max(0, limit - int(current_count))
                response.headers["X-RateLimit-Limit"] = str(limit)
                response.headers["X-RateLimit-Remaining"] = str(remaining)
                response.headers["X-RateLimit-Reset"] = str(int(time.time()) + window)
        except:
            pass  # Don't fail request if Redis is down

        return response


class RequestValidationMiddleware(BaseHTTPMiddleware):
    """Middleware for request validation and security checks."""

    def __init__(self, app):
        super().__init__(app)

        # Maximum request size (10MB)
        self.max_request_size = 10 * 1024 * 1024

        # Blocked user agents (basic bot protection)
        self.blocked_user_agents = [
            "sqlmap",
            "nikto",
            "wpscan",
            "gobuster",
            "dirb",
            "masscan",
            "nmap",
            "nuclei",
        ]

        # Suspicious patterns in URLs
        self.suspicious_patterns = [
            "../",
            "..\\",
            "/etc/passwd",
            "/proc/",
            "cmd.exe",
            "eval(",
            "javascript:",
            "vbscript:",
            "<script",
            "union select",
            "drop table",
            "insert into",
        ]

    def _is_suspicious_request(self, request: Request) -> bool:
        """Check if request contains suspicious patterns."""

        # Check URL path
        path = str(request.url.path).lower()
        for pattern in self.suspicious_patterns:
            if pattern in path:
                return True

        # Check query parameters
        query = str(request.url.query).lower()
        for pattern in self.suspicious_patterns:
            if pattern in query:
                return True

        # Check User-Agent
        user_agent = request.headers.get("User-Agent", "").lower()
        for blocked_agent in self.blocked_user_agents:
            if blocked_agent in user_agent:
                return True

        return False

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Validate request before processing."""

        # Check request size
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.max_request_size:
            logger.warning(
                f"Request too large: {content_length} bytes from {request.client.host if request.client else 'unknown'}"
            )
            return JSONResponse(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                content={"detail": "Requisição muito grande"},
            )

        # Check for suspicious patterns
        if self._is_suspicious_request(request):
            logger.warning(
                f"Suspicious request detected from {request.client.host if request.client else 'unknown'}: {request.url}"
            )
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"detail": "Requisição inválida"},
            )

        # Process request
        return await call_next(request)


class SecureCookieMiddleware(BaseHTTPMiddleware):
    """Middleware to ensure secure cookie settings."""

    def __init__(self, app, secure: bool = True, samesite: str = "lax"):
        super().__init__(app)
        self.secure = secure
        self.samesite = samesite

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process response and secure cookies."""

        response = await call_next(request)

        # Modify Set-Cookie headers to add security attributes
        if "set-cookie" in response.headers:
            cookies = response.headers.getlist("set-cookie")
            response.headers.pop("set-cookie")

            for cookie in cookies:
                # Add security attributes if not present
                if self.secure and "Secure" not in cookie:
                    cookie += "; Secure"

                if "HttpOnly" not in cookie and "HttpOnly" not in cookie:
                    cookie += "; HttpOnly"

                if "SameSite" not in cookie:
                    cookie += f"; SameSite={self.samesite}"

                response.headers.append("set-cookie", cookie)

        return response


def setup_security_middleware(app, redis_client=None, environment: str = "production"):
    """Set up all security middleware for the application."""

    # Add middleware in reverse order (last added is executed first)

    # Secure cookies (closest to response)
    app.add_middleware(
        SecureCookieMiddleware, secure=environment == "production", samesite="lax"
    )

    # Security headers
    app.add_middleware(SecurityHeadersMiddleware, environment=environment)

    # Request validation
    app.add_middleware(RequestValidationMiddleware)

    # Rate limiting (closest to request)
    if redis_client:
        app.add_middleware(RateLimitingMiddleware, redis_client=redis_client)

    logger.info("Security middleware configured successfully")
