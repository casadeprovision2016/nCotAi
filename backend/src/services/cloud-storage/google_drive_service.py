"""
Google Drive Service
Integration with Google Drive API for document storage and synchronization.
"""
import asyncio
import base64
import json
import logging
import mimetypes
import os
from datetime import datetime, timedelta
from typing import Any, BinaryIO, Dict, List, Optional
from urllib.parse import urlencode

import aiohttp

logger = logging.getLogger(__name__)


class GoogleDriveService:
    """Google Drive API integration service."""

    def __init__(self):
        self.client_id = os.getenv("GOOGLE_DRIVE_CLIENT_ID", "")
        self.client_secret = os.getenv("GOOGLE_DRIVE_CLIENT_SECRET", "")
        self.redirect_uri = os.getenv("GOOGLE_DRIVE_REDIRECT_URI", "")
        self.scopes = [
            "https://www.googleapis.com/auth/drive",
            "https://www.googleapis.com/auth/drive.file",
        ]

        # API URLs
        self.api_base_url = "https://www.googleapis.com/drive/v3"
        self.upload_url = "https://www.googleapis.com/upload/drive/v3/files"
        self.oauth_url = "https://oauth2.googleapis.com/token"
        self.auth_url = "https://accounts.google.com/o/oauth2/v2/auth"

        # Session management
        self.session = None
        self.access_token = None
        self.refresh_token = None
        self.token_expires_at = None

        # Rate limiting
        self.rate_limit_requests = 100
        self.rate_limit_window = 100  # seconds
        self.request_times = []

    async def initialize(self) -> Dict[str, Any]:
        """Initialize Google Drive service."""
        try:
            logger.info("Initializing Google Drive service")

            # Create HTTP session
            self.session = aiohttp.ClientSession()

            # Validate configuration
            if not all([self.client_id, self.client_secret, self.redirect_uri]):
                return {
                    "success": False,
                    "error": "Missing required Google Drive configuration",
                }

            logger.info("Google Drive service initialized successfully")
            return {
                "success": True,
                "message": "Google Drive service initialized",
                "scopes": self.scopes,
            }

        except Exception as e:
            logger.error(f"Error initializing Google Drive service: {str(e)}")
            return {"success": False, "error": str(e)}

    def get_authorization_url(self, state: Optional[str] = None) -> str:
        """Get OAuth2 authorization URL."""
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": " ".join(self.scopes),
            "response_type": "code",
            "access_type": "offline",
            "prompt": "consent",
        }

        if state:
            params["state"] = state

        return f"{self.auth_url}?{urlencode(params)}"

    async def exchange_code_for_tokens(self, authorization_code: str) -> Dict[str, Any]:
        """Exchange authorization code for access and refresh tokens."""
        try:
            data = {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "redirect_uri": self.redirect_uri,
                "grant_type": "authorization_code",
                "code": authorization_code,
            }

            async with self.session.post(self.oauth_url, data=data) as response:
                if response.status == 200:
                    token_data = await response.json()

                    self.access_token = token_data.get("access_token")
                    self.refresh_token = token_data.get("refresh_token")
                    expires_in = token_data.get("expires_in", 3600)
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
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "refresh_token": self.refresh_token,
                "grant_type": "refresh_token",
            }

            async with self.session.post(self.oauth_url, data=data) as response:
                if response.status == 200:
                    token_data = await response.json()

                    self.access_token = token_data.get("access_token")
                    expires_in = token_data.get("expires_in", 3600)
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
        file_name: Optional[str] = None,
        parent_folder_id: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Upload file to Google Drive."""
        try:
            if not await self._ensure_valid_token():
                return {"success": False, "error": "Invalid or missing access token"}

            await self._check_rate_limit()

            if not os.path.exists(file_path):
                return {"success": False, "error": "File not found"}

            # Prepare metadata
            if not file_name:
                file_name = os.path.basename(file_path)

            metadata = {"name": file_name}

            if parent_folder_id:
                metadata["parents"] = [parent_folder_id]

            if description:
                metadata["description"] = description

            # Detect MIME type
            mime_type, _ = mimetypes.guess_type(file_path)
            if not mime_type:
                mime_type = "application/octet-stream"

            # Upload using multipart request
            with open(file_path, "rb") as file_content:
                files = {
                    "metadata": (None, json.dumps(metadata), "application/json"),
                    "file": (file_name, file_content, mime_type),
                }

                headers = {"Authorization": f"Bearer {self.access_token}"}

                async with self.session.post(
                    f"{self.upload_url}?uploadType=multipart",
                    headers=headers,
                    data=files,
                ) as response:
                    if response.status in [200, 201]:
                        result = await response.json()

                        return {
                            "success": True,
                            "file_id": result.get("id"),
                            "file_name": result.get("name"),
                            "web_view_link": result.get("webViewLink"),
                            "download_link": result.get("webContentLink"),
                            "size": result.get("size"),
                            "created_time": result.get("createdTime"),
                        }
                    else:
                        error_data = await response.text()
                        return {
                            "success": False,
                            "error": f"Upload failed: {error_data}",
                        }

        except Exception as e:
            logger.error(f"Error uploading file to Google Drive: {str(e)}")
            return {"success": False, "error": str(e)}

    async def download_file(self, file_id: str, download_path: str) -> Dict[str, Any]:
        """Download file from Google Drive."""
        try:
            if not await self._ensure_valid_token():
                return {"success": False, "error": "Invalid or missing access token"}

            await self._check_rate_limit()

            headers = self._get_headers()

            async with self.session.get(
                f"{self.api_base_url}/files/{file_id}?alt=media", headers=headers
            ) as response:
                if response.status == 200:
                    # Create download directory if it doesn't exist
                    os.makedirs(os.path.dirname(download_path), exist_ok=True)

                    with open(download_path, "wb") as f:
                        async for chunk in response.content.iter_chunked(8192):
                            f.write(chunk)

                    return {
                        "success": True,
                        "file_path": download_path,
                        "size": os.path.getsize(download_path),
                    }
                else:
                    error_data = await response.text()
                    return {"success": False, "error": f"Download failed: {error_data}"}

        except Exception as e:
            logger.error(f"Error downloading file from Google Drive: {str(e)}")
            return {"success": False, "error": str(e)}

    async def create_folder(
        self, folder_name: str, parent_folder_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create folder in Google Drive."""
        try:
            if not await self._ensure_valid_token():
                return {"success": False, "error": "Invalid or missing access token"}

            await self._check_rate_limit()

            metadata = {
                "name": folder_name,
                "mimeType": "application/vnd.google-apps.folder",
            }

            if parent_folder_id:
                metadata["parents"] = [parent_folder_id]

            headers = self._get_headers()

            async with self.session.post(
                f"{self.api_base_url}/files", headers=headers, json=metadata
            ) as response:
                if response.status in [200, 201]:
                    result = await response.json()

                    return {
                        "success": True,
                        "folder_id": result.get("id"),
                        "folder_name": result.get("name"),
                        "web_view_link": result.get("webViewLink"),
                        "created_time": result.get("createdTime"),
                    }
                else:
                    error_data = await response.text()
                    return {
                        "success": False,
                        "error": f"Folder creation failed: {error_data}",
                    }

        except Exception as e:
            logger.error(f"Error creating folder in Google Drive: {str(e)}")
            return {"success": False, "error": str(e)}

    async def list_files(
        self,
        parent_folder_id: Optional[str] = None,
        query: Optional[str] = None,
        max_results: int = 100,
    ) -> Dict[str, Any]:
        """List files in Google Drive."""
        try:
            if not await self._ensure_valid_token():
                return {"success": False, "error": "Invalid or missing access token"}

            await self._check_rate_limit()

            # Build query
            query_parts = []
            if parent_folder_id:
                query_parts.append(f"'{parent_folder_id}' in parents")
            if query:
                query_parts.append(query)

            params = {
                "pageSize": min(max_results, 1000),
                "fields": "nextPageToken, files(id, name, size, createdTime, modifiedTime, mimeType, webViewLink, webContentLink)",
            }

            if query_parts:
                params["q"] = " and ".join(query_parts)

            headers = self._get_headers()

            async with self.session.get(
                f"{self.api_base_url}/files", headers=headers, params=params
            ) as response:
                if response.status == 200:
                    result = await response.json()

                    return {
                        "success": True,
                        "files": result.get("files", []),
                        "next_page_token": result.get("nextPageToken"),
                    }
                else:
                    error_data = await response.text()
                    return {
                        "success": False,
                        "error": f"File listing failed: {error_data}",
                    }

        except Exception as e:
            logger.error(f"Error listing files in Google Drive: {str(e)}")
            return {"success": False, "error": str(e)}

    async def share_file(
        self,
        file_id: str,
        email: Optional[str] = None,
        role: str = "reader",
        type_: str = "user",
    ) -> Dict[str, Any]:
        """Share file in Google Drive."""
        try:
            if not await self._ensure_valid_token():
                return {"success": False, "error": "Invalid or missing access token"}

            await self._check_rate_limit()

            permission = {"role": role, "type": type_}

            if email and type_ == "user":
                permission["emailAddress"] = email

            headers = self._get_headers()

            async with self.session.post(
                f"{self.api_base_url}/files/{file_id}/permissions",
                headers=headers,
                json=permission,
            ) as response:
                if response.status in [200, 201]:
                    result = await response.json()

                    return {
                        "success": True,
                        "permission_id": result.get("id"),
                        "role": result.get("role"),
                        "type": result.get("type"),
                    }
                else:
                    error_data = await response.text()
                    return {
                        "success": False,
                        "error": f"File sharing failed: {error_data}",
                    }

        except Exception as e:
            logger.error(f"Error sharing file in Google Drive: {str(e)}")
            return {"success": False, "error": str(e)}

    async def delete_file(self, file_id: str) -> Dict[str, Any]:
        """Delete file from Google Drive."""
        try:
            if not await self._ensure_valid_token():
                return {"success": False, "error": "Invalid or missing access token"}

            await self._check_rate_limit()

            headers = self._get_headers()

            async with self.session.delete(
                f"{self.api_base_url}/files/{file_id}", headers=headers
            ) as response:
                if response.status == 204:
                    return {"success": True, "message": "File deleted successfully"}
                else:
                    error_data = await response.text()
                    return {
                        "success": False,
                        "error": f"File deletion failed: {error_data}",
                    }

        except Exception as e:
            logger.error(f"Error deleting file from Google Drive: {str(e)}")
            return {"success": False, "error": str(e)}

    async def get_user_info(self) -> Dict[str, Any]:
        """Get information about the authenticated user."""
        try:
            if not await self._ensure_valid_token():
                return {"success": False, "error": "Invalid or missing access token"}

            await self._check_rate_limit()

            headers = self._get_headers()

            async with self.session.get(
                f"{self.api_base_url}/about?fields=user,storageQuota", headers=headers
            ) as response:
                if response.status == 200:
                    result = await response.json()

                    return {
                        "success": True,
                        "user": result.get("user", {}),
                        "storage_quota": result.get("storageQuota", {}),
                    }
                else:
                    error_data = await response.text()
                    return {
                        "success": False,
                        "error": f"User info request failed: {error_data}",
                    }

        except Exception as e:
            logger.error(f"Error getting user info from Google Drive: {str(e)}")
            return {"success": False, "error": str(e)}

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check for Google Drive service."""
        try:
            if not await self._ensure_valid_token():
                return {"status": "error", "message": "Invalid or missing access token"}

            # Try to get user info as a health check
            user_info = await self.get_user_info()

            if user_info.get("success"):
                return {
                    "status": "healthy",
                    "message": "Google Drive service is operational",
                    "user_email": user_info.get("user", {}).get("emailAddress"),
                    "last_check": datetime.utcnow().isoformat(),
                }
            else:
                return {
                    "status": "error",
                    "message": "Google Drive API is not accessible",
                    "error": user_info.get("error"),
                }

        except Exception as e:
            logger.error(f"Google Drive health check failed: {str(e)}")
            return {
                "status": "error",
                "message": "Health check failed",
                "error": str(e),
            }

    async def cleanup(self) -> Dict[str, Any]:
        """Cleanup Google Drive service resources."""
        try:
            if self.session:
                await self.session.close()
                self.session = None

            self.access_token = None
            self.refresh_token = None
            self.token_expires_at = None

            return {
                "status": "success",
                "message": "Google Drive service cleaned up successfully",
            }

        except Exception as e:
            logger.error(f"Error cleaning up Google Drive service: {str(e)}")
            return {"status": "error", "error": str(e)}
