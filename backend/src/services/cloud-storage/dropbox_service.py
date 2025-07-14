"""
Dropbox Service
Integration with Dropbox API for document storage and synchronization.
"""
import asyncio
import hashlib
import hmac
import json
import logging
import os
from datetime import datetime, timedelta
from typing import Any, BinaryIO, Dict, List, Optional
from urllib.parse import urlencode

import aiohttp

logger = logging.getLogger(__name__)


class DropboxService:
    """Dropbox API integration service."""

    def __init__(self):
        self.app_key = os.getenv("DROPBOX_APP_KEY", "")
        self.app_secret = os.getenv("DROPBOX_APP_SECRET", "")
        self.redirect_uri = os.getenv("DROPBOX_REDIRECT_URI", "")

        # API URLs
        self.api_base_url = "https://api.dropboxapi.com/2"
        self.content_api_url = "https://content.dropboxapi.com/2"
        self.oauth_url = "https://api.dropboxapi.com/oauth2/token"
        self.auth_url = "https://www.dropbox.com/oauth2/authorize"

        # Session management
        self.session = None
        self.access_token = None
        self.refresh_token = None
        self.token_expires_at = None

        # Rate limiting
        self.rate_limit_requests = 120
        self.rate_limit_window = 60  # seconds
        self.request_times = []

    async def initialize(self) -> Dict[str, Any]:
        """Initialize Dropbox service."""
        try:
            logger.info("Initializing Dropbox service")

            # Create HTTP session
            self.session = aiohttp.ClientSession()

            # Validate configuration
            if not all([self.app_key, self.app_secret, self.redirect_uri]):
                return {
                    "success": False,
                    "error": "Missing required Dropbox configuration",
                }

            logger.info("Dropbox service initialized successfully")
            return {"success": True, "message": "Dropbox service initialized"}

        except Exception as e:
            logger.error(f"Error initializing Dropbox service: {str(e)}")
            return {"success": False, "error": str(e)}

    def get_authorization_url(self, state: Optional[str] = None) -> str:
        """Get OAuth2 authorization URL."""
        params = {
            "client_id": self.app_key,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "token_access_type": "offline",
        }

        if state:
            params["state"] = state

        return f"{self.auth_url}?{urlencode(params)}"

    async def exchange_code_for_tokens(self, authorization_code: str) -> Dict[str, Any]:
        """Exchange authorization code for access and refresh tokens."""
        try:
            data = {
                "code": authorization_code,
                "grant_type": "authorization_code",
                "client_id": self.app_key,
                "client_secret": self.app_secret,
                "redirect_uri": self.redirect_uri,
            }

            async with self.session.post(self.oauth_url, data=data) as response:
                if response.status == 200:
                    token_data = await response.json()

                    self.access_token = token_data.get("access_token")
                    self.refresh_token = token_data.get("refresh_token")
                    expires_in = token_data.get("expires_in", 14400)  # 4 hours default
                    self.token_expires_at = datetime.utcnow() + timedelta(
                        seconds=expires_in
                    )

                    return {
                        "success": True,
                        "access_token": self.access_token,
                        "refresh_token": self.refresh_token,
                        "expires_at": self.token_expires_at.isoformat(),
                    }
                else:
                    error_data = await response.text()
                    return {
                        "success": False,
                        "error": f"Token exchange failed: {error_data}",
                    }

        except Exception as e:
            logger.error(f"Error exchanging code for tokens: {str(e)}")
            return {"success": False, "error": str(e)}

    async def refresh_access_token(self) -> Dict[str, Any]:
        """Refresh access token using refresh token."""
        try:
            if not self.refresh_token:
                return {"success": False, "error": "No refresh token available"}

            data = {
                "grant_type": "refresh_token",
                "refresh_token": self.refresh_token,
                "client_id": self.app_key,
                "client_secret": self.app_secret,
            }

            async with self.session.post(self.oauth_url, data=data) as response:
                if response.status == 200:
                    token_data = await response.json()

                    self.access_token = token_data.get("access_token")
                    expires_in = token_data.get("expires_in", 14400)
                    self.token_expires_at = datetime.utcnow() + timedelta(
                        seconds=expires_in
                    )

                    # Update refresh token if provided
                    if "refresh_token" in token_data:
                        self.refresh_token = token_data["refresh_token"]

                    return {
                        "success": True,
                        "access_token": self.access_token,
                        "expires_at": self.token_expires_at.isoformat(),
                    }
                else:
                    error_data = await response.text()
                    return {
                        "success": False,
                        "error": f"Token refresh failed: {error_data}",
                    }

        except Exception as e:
            logger.error(f"Error refreshing access token: {str(e)}")
            return {"success": False, "error": str(e)}

    async def _ensure_valid_token(self) -> bool:
        """Ensure we have a valid access token."""
        if not self.access_token:
            return False

        if (
            self.token_expires_at
            and datetime.utcnow() >= self.token_expires_at - timedelta(minutes=5)
        ):
            refresh_result = await self.refresh_access_token()
            return refresh_result.get("success", False)

        return True

    def _get_headers(self) -> Dict[str, str]:
        """Get headers for API requests."""
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    async def _check_rate_limit(self):
        """Check and enforce rate limiting."""
        now = datetime.utcnow()
        # Remove old requests outside the window
        self.request_times = [
            req_time
            for req_time in self.request_times
            if now - req_time < timedelta(seconds=self.rate_limit_window)
        ]

        if len(self.request_times) >= self.rate_limit_requests:
            sleep_time = (
                self.rate_limit_window - (now - self.request_times[0]).total_seconds()
            )
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)

        self.request_times.append(now)

    async def upload_file(
        self,
        file_path: str,
        dropbox_path: str,
        mode: str = "add",
        autorename: bool = False,
    ) -> Dict[str, Any]:
        """Upload file to Dropbox."""
        try:
            if not await self._ensure_valid_token():
                return {"success": False, "error": "Invalid or missing access token"}

            await self._check_rate_limit()

            if not os.path.exists(file_path):
                return {"success": False, "error": "File not found"}

            # Prepare upload parameters
            args = {"path": dropbox_path, "mode": mode, "autorename": autorename}

            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Dropbox-API-Arg": json.dumps(args),
                "Content-Type": "application/octet-stream",
            }

            # Upload file
            with open(file_path, "rb") as file_content:
                async with self.session.post(
                    f"{self.content_api_url}/files/upload",
                    headers=headers,
                    data=file_content,
                ) as response:
                    if response.status == 200:
                        result = await response.json()

                        return {
                            "success": True,
                            "file_id": result.get("id"),
                            "file_name": result.get("name"),
                            "path_lower": result.get("path_lower"),
                            "size": result.get("size"),
                            "server_modified": result.get("server_modified"),
                            "content_hash": result.get("content_hash"),
                        }
                    else:
                        error_data = await response.text()
                        return {
                            "success": False,
                            "error": f"Upload failed: {error_data}",
                        }

        except Exception as e:
            logger.error(f"Error uploading file to Dropbox: {str(e)}")
            return {"success": False, "error": str(e)}

    async def download_file(
        self, dropbox_path: str, download_path: str
    ) -> Dict[str, Any]:
        """Download file from Dropbox."""
        try:
            if not await self._ensure_valid_token():
                return {"success": False, "error": "Invalid or missing access token"}

            await self._check_rate_limit()

            args = {"path": dropbox_path}

            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Dropbox-API-Arg": json.dumps(args),
            }

            async with self.session.post(
                f"{self.content_api_url}/files/download", headers=headers
            ) as response:
                if response.status == 200:
                    # Create download directory if it doesn't exist
                    os.makedirs(os.path.dirname(download_path), exist_ok=True)

                    with open(download_path, "wb") as f:
                        async for chunk in response.content.iter_chunked(8192):
                            f.write(chunk)

                    # Get metadata from response headers
                    api_result = response.headers.get("Dropbox-API-Result")
                    metadata = json.loads(api_result) if api_result else {}

                    return {
                        "success": True,
                        "file_path": download_path,
                        "size": os.path.getsize(download_path),
                        "metadata": metadata,
                    }
                else:
                    error_data = await response.text()
                    return {"success": False, "error": f"Download failed: {error_data}"}

        except Exception as e:
            logger.error(f"Error downloading file from Dropbox: {str(e)}")
            return {"success": False, "error": str(e)}

    async def create_folder(self, folder_path: str) -> Dict[str, Any]:
        """Create folder in Dropbox."""
        try:
            if not await self._ensure_valid_token():
                return {"success": False, "error": "Invalid or missing access token"}

            await self._check_rate_limit()

            data = {"path": folder_path}
            headers = self._get_headers()

            async with self.session.post(
                f"{self.api_base_url}/files/create_folder_v2",
                headers=headers,
                json=data,
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    metadata = result.get("metadata", {})

                    return {
                        "success": True,
                        "folder_id": metadata.get("id"),
                        "folder_name": metadata.get("name"),
                        "path_lower": metadata.get("path_lower"),
                        "path_display": metadata.get("path_display"),
                    }
                else:
                    error_data = await response.text()
                    return {
                        "success": False,
                        "error": f"Folder creation failed: {error_data}",
                    }

        except Exception as e:
            logger.error(f"Error creating folder in Dropbox: {str(e)}")
            return {"success": False, "error": str(e)}

    async def list_files(
        self, folder_path: str = "", recursive: bool = False, limit: int = 2000
    ) -> Dict[str, Any]:
        """List files in Dropbox folder."""
        try:
            if not await self._ensure_valid_token():
                return {"success": False, "error": "Invalid or missing access token"}

            await self._check_rate_limit()

            data = {
                "path": folder_path,
                "recursive": recursive,
                "limit": min(limit, 2000),
            }

            headers = self._get_headers()

            async with self.session.post(
                f"{self.api_base_url}/files/list_folder", headers=headers, json=data
            ) as response:
                if response.status == 200:
                    result = await response.json()

                    return {
                        "success": True,
                        "entries": result.get("entries", []),
                        "cursor": result.get("cursor"),
                        "has_more": result.get("has_more", False),
                    }
                else:
                    error_data = await response.text()
                    return {
                        "success": False,
                        "error": f"File listing failed: {error_data}",
                    }

        except Exception as e:
            logger.error(f"Error listing files in Dropbox: {str(e)}")
            return {"success": False, "error": str(e)}

    async def get_sharing_link(
        self, dropbox_path: str, link_type: str = "preview"
    ) -> Dict[str, Any]:
        """Get sharing link for Dropbox file."""
        try:
            if not await self._ensure_valid_token():
                return {"success": False, "error": "Invalid or missing access token"}

            await self._check_rate_limit()

            data = {
                "path": dropbox_path,
                "settings": {
                    "requested_visibility": "public"
                    if link_type == "direct"
                    else "team_and_password",
                    "audience": "public",
                    "access": "viewer",
                },
            }

            headers = self._get_headers()

            async with self.session.post(
                f"{self.api_base_url}/sharing/create_shared_link_with_settings",
                headers=headers,
                json=data,
            ) as response:
                if response.status == 200:
                    result = await response.json()

                    return {
                        "success": True,
                        "url": result.get("url"),
                        "expires": result.get("expires"),
                        "link_permissions": result.get("link_permissions", {}),
                        "team_member_info": result.get("team_member_info", {}),
                    }
                else:
                    error_data = await response.text()
                    return {
                        "success": False,
                        "error": f"Sharing link creation failed: {error_data}",
                    }

        except Exception as e:
            logger.error(f"Error creating sharing link in Dropbox: {str(e)}")
            return {"success": False, "error": str(e)}

    async def delete_file(self, dropbox_path: str) -> Dict[str, Any]:
        """Delete file from Dropbox."""
        try:
            if not await self._ensure_valid_token():
                return {"success": False, "error": "Invalid or missing access token"}

            await self._check_rate_limit()

            data = {"path": dropbox_path}
            headers = self._get_headers()

            async with self.session.post(
                f"{self.api_base_url}/files/delete_v2", headers=headers, json=data
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    metadata = result.get("metadata", {})

                    return {
                        "success": True,
                        "deleted_file": metadata.get("name"),
                        "path_lower": metadata.get("path_lower"),
                    }
                else:
                    error_data = await response.text()
                    return {
                        "success": False,
                        "error": f"File deletion failed: {error_data}",
                    }

        except Exception as e:
            logger.error(f"Error deleting file from Dropbox: {str(e)}")
            return {"success": False, "error": str(e)}

    async def get_user_info(self) -> Dict[str, Any]:
        """Get information about the authenticated user."""
        try:
            if not await self._ensure_valid_token():
                return {"success": False, "error": "Invalid or missing access token"}

            await self._check_rate_limit()

            headers = self._get_headers()

            async with self.session.post(
                f"{self.api_base_url}/users/get_current_account", headers=headers
            ) as response:
                if response.status == 200:
                    result = await response.json()

                    return {
                        "success": True,
                        "account_id": result.get("account_id"),
                        "name": result.get("name", {}),
                        "email": result.get("email"),
                        "email_verified": result.get("email_verified"),
                        "profile_photo_url": result.get("profile_photo_url"),
                        "country": result.get("country"),
                    }
                else:
                    error_data = await response.text()
                    return {
                        "success": False,
                        "error": f"User info request failed: {error_data}",
                    }

        except Exception as e:
            logger.error(f"Error getting user info from Dropbox: {str(e)}")
            return {"success": False, "error": str(e)}

    async def get_space_usage(self) -> Dict[str, Any]:
        """Get space usage information."""
        try:
            if not await self._ensure_valid_token():
                return {"success": False, "error": "Invalid or missing access token"}

            await self._check_rate_limit()

            headers = self._get_headers()

            async with self.session.post(
                f"{self.api_base_url}/users/get_space_usage", headers=headers
            ) as response:
                if response.status == 200:
                    result = await response.json()

                    return {
                        "success": True,
                        "used": result.get("used"),
                        "allocation": result.get("allocation", {}),
                    }
                else:
                    error_data = await response.text()
                    return {
                        "success": False,
                        "error": f"Space usage request failed: {error_data}",
                    }

        except Exception as e:
            logger.error(f"Error getting space usage from Dropbox: {str(e)}")
            return {"success": False, "error": str(e)}

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check for Dropbox service."""
        try:
            if not await self._ensure_valid_token():
                return {"status": "error", "message": "Invalid or missing access token"}

            # Try to get user info as a health check
            user_info = await self.get_user_info()

            if user_info.get("success"):
                return {
                    "status": "healthy",
                    "message": "Dropbox service is operational",
                    "user_email": user_info.get("email"),
                    "last_check": datetime.utcnow().isoformat(),
                }
            else:
                return {
                    "status": "error",
                    "message": "Dropbox API is not accessible",
                    "error": user_info.get("error"),
                }

        except Exception as e:
            logger.error(f"Dropbox health check failed: {str(e)}")
            return {
                "status": "error",
                "message": "Health check failed",
                "error": str(e),
            }

    async def cleanup(self) -> Dict[str, Any]:
        """Cleanup Dropbox service resources."""
        try:
            if self.session:
                await self.session.close()
                self.session = None

            self.access_token = None
            self.refresh_token = None
            self.token_expires_at = None

            return {
                "status": "success",
                "message": "Dropbox service cleaned up successfully",
            }

        except Exception as e:
            logger.error(f"Error cleaning up Dropbox service: {str(e)}")
            return {"status": "error", "error": str(e)}
