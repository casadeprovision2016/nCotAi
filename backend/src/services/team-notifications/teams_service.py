"""
Microsoft Teams Service
Integration with Microsoft Teams API for team notifications and workflow automation.
"""
import asyncio
import base64
import json
import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

import aiohttp

logger = logging.getLogger(__name__)


class MicrosoftTeamsService:
    """Microsoft Teams API integration service."""

    def __init__(self):
        self.client_id = os.getenv("TEAMS_CLIENT_ID", "")
        self.client_secret = os.getenv("TEAMS_CLIENT_SECRET", "")
        self.tenant_id = os.getenv("TEAMS_TENANT_ID", "")
        self.redirect_uri = os.getenv("TEAMS_REDIRECT_URI", "")

        # Scopes
        self.scopes = [
            "https://graph.microsoft.com/Chat.ReadWrite",
            "https://graph.microsoft.com/Team.ReadBasic.All",
            "https://graph.microsoft.com/Channel.ReadBasic.All",
            "https://graph.microsoft.com/ChannelMessage.Send",
            "https://graph.microsoft.com/Files.ReadWrite",
        ]

        # API URLs
        self.graph_base_url = "https://graph.microsoft.com/v1.0"
        self.auth_url = (
            f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/authorize"
        )
        self.token_url = (
            f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
        )

        # Session management
        self.session = None
        self.access_token = None
        self.refresh_token = None
        self.token_expires_at = None

        # Rate limiting
        self.rate_limit_requests = 10000
        self.rate_limit_window = 600  # 10 minutes
        self.request_times = []

    async def initialize(self) -> Dict[str, Any]:
        """Initialize Microsoft Teams service."""
        try:
            logger.info("Initializing Microsoft Teams service")

            # Create HTTP session
            self.session = aiohttp.ClientSession()

            # Validate configuration
            if not all([self.client_id, self.client_secret, self.tenant_id]):
                return {
                    "success": False,
                    "error": "Missing required Microsoft Teams configuration",
                }

            logger.info("Microsoft Teams service initialized successfully")
            return {
                "success": True,
                "message": "Microsoft Teams service initialized",
                "scopes": self.scopes,
            }

        except Exception as e:
            logger.error(f"Error initializing Microsoft Teams service: {str(e)}")
            return {"success": False, "error": str(e)}

    def get_authorization_url(self, state: Optional[str] = None) -> str:
        """Get OAuth2 authorization URL."""
        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "redirect_uri": self.redirect_uri,
            "scope": " ".join(self.scopes),
            "response_mode": "query",
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
                "code": authorization_code,
                "grant_type": "authorization_code",
                "redirect_uri": self.redirect_uri,
            }

            async with self.session.post(self.token_url, data=data) as response:
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
                        "scope": token_data.get("scope"),
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

            async with self.session.post(self.token_url, data=data) as response:
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

    async def send_channel_message(
        self, team_id: str, channel_id: str, message: str, message_type: str = "text"
    ) -> Dict[str, Any]:
        """Send message to Teams channel."""
        try:
            if not await self._ensure_valid_token():
                return {"success": False, "error": "Invalid or missing access token"}

            await self._check_rate_limit()

            data = {"body": {"contentType": message_type, "content": message}}

            headers = self._get_headers()

            async with self.session.post(
                f"{self.graph_base_url}/teams/{team_id}/channels/{channel_id}/messages",
                headers=headers,
                json=data,
            ) as response:
                if response.status in [200, 201]:
                    result = await response.json()

                    return {
                        "success": True,
                        "message_id": result.get("id"),
                        "web_url": result.get("webUrl"),
                        "created_datetime": result.get("createdDateTime"),
                    }
                else:
                    error_data = await response.text()
                    return {
                        "success": False,
                        "error": f"Message sending failed: {error_data}",
                    }

        except Exception as e:
            logger.error(f"Error sending Teams message: {str(e)}")
            return {"success": False, "error": str(e)}

    async def send_adaptive_card_message(
        self, team_id: str, channel_id: str, card_content: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Send adaptive card message to Teams channel."""
        try:
            if not await self._ensure_valid_token():
                return {"success": False, "error": "Invalid or missing access token"}

            await self._check_rate_limit()

            data = {
                "body": {
                    "contentType": "html",
                    "content": '<attachment id="adaptive_card"></attachment>',
                },
                "attachments": [
                    {
                        "id": "adaptive_card",
                        "contentType": "application/vnd.microsoft.card.adaptive",
                        "content": card_content,
                    }
                ],
            }

            headers = self._get_headers()

            async with self.session.post(
                f"{self.graph_base_url}/teams/{team_id}/channels/{channel_id}/messages",
                headers=headers,
                json=data,
            ) as response:
                if response.status in [200, 201]:
                    result = await response.json()

                    return {
                        "success": True,
                        "message_id": result.get("id"),
                        "web_url": result.get("webUrl"),
                        "created_datetime": result.get("createdDateTime"),
                    }
                else:
                    error_data = await response.text()
                    return {
                        "success": False,
                        "error": f"Adaptive card message sending failed: {error_data}",
                    }

        except Exception as e:
            logger.error(f"Error sending adaptive card message: {str(e)}")
            return {"success": False, "error": str(e)}

    async def create_team(
        self, display_name: str, description: str, visibility: str = "private"
    ) -> Dict[str, Any]:
        """Create new Teams team."""
        try:
            if not await self._ensure_valid_token():
                return {"success": False, "error": "Invalid or missing access token"}

            await self._check_rate_limit()

            data = {
                "template@odata.bind": "https://graph.microsoft.com/v1.0/teamsTemplates('standard')",
                "displayName": display_name,
                "description": description,
                "visibility": visibility,
            }

            headers = self._get_headers()

            async with self.session.post(
                f"{self.graph_base_url}/teams", headers=headers, json=data
            ) as response:
                if response.status in [201, 202]:
                    # Team creation is async, get location header
                    location = response.headers.get("Location")

                    return {
                        "success": True,
                        "message": "Team creation initiated",
                        "location": location,
                    }
                else:
                    error_data = await response.text()
                    return {
                        "success": False,
                        "error": f"Team creation failed: {error_data}",
                    }

        except Exception as e:
            logger.error(f"Error creating team: {str(e)}")
            return {"success": False, "error": str(e)}

    async def create_channel(
        self,
        team_id: str,
        display_name: str,
        description: Optional[str] = None,
        membership_type: str = "standard",
    ) -> Dict[str, Any]:
        """Create channel in Teams team."""
        try:
            if not await self._ensure_valid_token():
                return {"success": False, "error": "Invalid or missing access token"}

            await self._check_rate_limit()

            data = {"displayName": display_name, "membershipType": membership_type}

            if description:
                data["description"] = description

            headers = self._get_headers()

            async with self.session.post(
                f"{self.graph_base_url}/teams/{team_id}/channels",
                headers=headers,
                json=data,
            ) as response:
                if response.status in [200, 201]:
                    result = await response.json()

                    return {
                        "success": True,
                        "channel_id": result.get("id"),
                        "display_name": result.get("displayName"),
                        "web_url": result.get("webUrl"),
                    }
                else:
                    error_data = await response.text()
                    return {
                        "success": False,
                        "error": f"Channel creation failed: {error_data}",
                    }

        except Exception as e:
            logger.error(f"Error creating channel: {str(e)}")
            return {"success": False, "error": str(e)}

    async def get_teams(self) -> Dict[str, Any]:
        """Get list of teams."""
        try:
            if not await self._ensure_valid_token():
                return {"success": False, "error": "Invalid or missing access token"}

            await self._check_rate_limit()

            headers = self._get_headers()

            async with self.session.get(
                f"{self.graph_base_url}/me/joinedTeams", headers=headers
            ) as response:
                if response.status == 200:
                    result = await response.json()

                    return {"success": True, "teams": result.get("value", [])}
                else:
                    error_data = await response.text()
                    return {
                        "success": False,
                        "error": f"Getting teams failed: {error_data}",
                    }

        except Exception as e:
            logger.error(f"Error getting teams: {str(e)}")
            return {"success": False, "error": str(e)}

    async def get_channels(self, team_id: str) -> Dict[str, Any]:
        """Get channels in a team."""
        try:
            if not await self._ensure_valid_token():
                return {"success": False, "error": "Invalid or missing access token"}

            await self._check_rate_limit()

            headers = self._get_headers()

            async with self.session.get(
                f"{self.graph_base_url}/teams/{team_id}/channels", headers=headers
            ) as response:
                if response.status == 200:
                    result = await response.json()

                    return {"success": True, "channels": result.get("value", [])}
                else:
                    error_data = await response.text()
                    return {
                        "success": False,
                        "error": f"Getting channels failed: {error_data}",
                    }

        except Exception as e:
            logger.error(f"Error getting channels: {str(e)}")
            return {"success": False, "error": str(e)}

    async def upload_file_to_channel(
        self,
        team_id: str,
        channel_id: str,
        file_path: str,
        file_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Upload file to Teams channel."""
        try:
            if not await self._ensure_valid_token():
                return {"success": False, "error": "Invalid or missing access token"}

            await self._check_rate_limit()

            if not os.path.exists(file_path):
                return {"success": False, "error": "File not found"}

            if not file_name:
                file_name = os.path.basename(file_path)

            headers = self._get_headers()
            headers["Content-Type"] = "application/octet-stream"

            # Upload to SharePoint site associated with the team
            with open(file_path, "rb") as file_content:
                async with self.session.put(
                    f"{self.graph_base_url}/teams/{team_id}/channels/{channel_id}/filesFolder:/{file_name}:/content",
                    headers=headers,
                    data=file_content,
                ) as response:
                    if response.status in [200, 201]:
                        result = await response.json()

                        return {
                            "success": True,
                            "file_id": result.get("id"),
                            "file_name": result.get("name"),
                            "web_url": result.get("webUrl"),
                            "download_url": result.get("@microsoft.graph.downloadUrl"),
                        }
                    else:
                        error_data = await response.text()
                        return {
                            "success": False,
                            "error": f"File upload failed: {error_data}",
                        }

        except Exception as e:
            logger.error(f"Error uploading file to Teams: {str(e)}")
            return {"success": False, "error": str(e)}

    async def add_member_to_team(
        self, team_id: str, user_id: str, role: str = "member"
    ) -> Dict[str, Any]:
        """Add member to team."""
        try:
            if not await self._ensure_valid_token():
                return {"success": False, "error": "Invalid or missing access token"}

            await self._check_rate_limit()

            data = {
                "@odata.type": "#microsoft.graph.aadUserConversationMember",
                "user@odata.bind": f"https://graph.microsoft.com/v1.0/users('{user_id}')",
                "roles": [role],
            }

            headers = self._get_headers()

            async with self.session.post(
                f"{self.graph_base_url}/teams/{team_id}/members",
                headers=headers,
                json=data,
            ) as response:
                if response.status in [200, 201]:
                    result = await response.json()

                    return {
                        "success": True,
                        "member_id": result.get("id"),
                        "display_name": result.get("displayName"),
                        "roles": result.get("roles", []),
                    }
                else:
                    error_data = await response.text()
                    return {
                        "success": False,
                        "error": f"Adding member failed: {error_data}",
                    }

        except Exception as e:
            logger.error(f"Error adding member to team: {str(e)}")
            return {"success": False, "error": str(e)}

    async def get_user_profile(self) -> Dict[str, Any]:
        """Get current user profile."""
        try:
            if not await self._ensure_valid_token():
                return {"success": False, "error": "Invalid or missing access token"}

            await self._check_rate_limit()

            headers = self._get_headers()

            async with self.session.get(
                f"{self.graph_base_url}/me", headers=headers
            ) as response:
                if response.status == 200:
                    result = await response.json()

                    return {
                        "success": True,
                        "user_id": result.get("id"),
                        "display_name": result.get("displayName"),
                        "mail": result.get("mail"),
                        "user_principal_name": result.get("userPrincipalName"),
                    }
                else:
                    error_data = await response.text()
                    return {
                        "success": False,
                        "error": f"Getting user profile failed: {error_data}",
                    }

        except Exception as e:
            logger.error(f"Error getting user profile: {str(e)}")
            return {"success": False, "error": str(e)}

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check for Microsoft Teams service."""
        try:
            if not await self._ensure_valid_token():
                return {"status": "error", "message": "Invalid or missing access token"}

            # Try to get user profile as a health check
            user_profile = await self.get_user_profile()

            if user_profile.get("success"):
                return {
                    "status": "healthy",
                    "message": "Microsoft Teams service is operational",
                    "user_email": user_profile.get("mail"),
                    "last_check": datetime.utcnow().isoformat(),
                }
            else:
                return {
                    "status": "error",
                    "message": "Microsoft Graph API is not accessible",
                    "error": user_profile.get("error"),
                }

        except Exception as e:
            logger.error(f"Microsoft Teams health check failed: {str(e)}")
            return {
                "status": "error",
                "message": "Health check failed",
                "error": str(e),
            }

    async def cleanup(self) -> Dict[str, Any]:
        """Cleanup Microsoft Teams service resources."""
        try:
            if self.session:
                await self.session.close()
                self.session = None

            self.access_token = None
            self.refresh_token = None
            self.token_expires_at = None

            return {
                "status": "success",
                "message": "Microsoft Teams service cleaned up successfully",
            }

        except Exception as e:
            logger.error(f"Error cleaning up Microsoft Teams service: {str(e)}")
            return {"status": "error", "error": str(e)}
