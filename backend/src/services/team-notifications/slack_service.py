"""
Slack Service
Integration with Slack API for team notifications and workflow automation.
"""
import asyncio
import json
import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

import aiohttp

logger = logging.getLogger(__name__)


class SlackService:
    """Slack API integration service."""

    def __init__(self):
        self.bot_token = os.getenv("SLACK_BOT_TOKEN", "")
        self.app_token = os.getenv("SLACK_APP_TOKEN", "")
        self.client_id = os.getenv("SLACK_CLIENT_ID", "")
        self.client_secret = os.getenv("SLACK_CLIENT_SECRET", "")
        self.signing_secret = os.getenv("SLACK_SIGNING_SECRET", "")

        # API URLs
        self.api_base_url = "https://slack.com/api"
        self.oauth_url = "https://slack.com/api/oauth.v2.access"
        self.auth_url = "https://slack.com/oauth/v2/authorize"

        # Session management
        self.session = None

        # Rate limiting
        self.rate_limit_tier = 1  # Tier 1: 1+ requests per minute
        self.rate_limit_requests = 50
        self.rate_limit_window = 60  # seconds
        self.request_times = []

        # Bot configuration
        self.bot_user_id = None
        self.workspace_info = None

    async def initialize(self) -> Dict[str, Any]:
        """Initialize Slack service."""
        try:
            logger.info("Initializing Slack service")

            # Create HTTP session
            self.session = aiohttp.ClientSession()

            # Validate configuration
            if not self.bot_token:
                return {"success": False, "error": "Missing required Slack bot token"}

            # Test authentication and get bot info
            auth_test = await self.test_auth()
            if not auth_test.get("success"):
                return auth_test

            self.bot_user_id = auth_test.get("user_id")
            self.workspace_info = {
                "team_id": auth_test.get("team_id"),
                "team": auth_test.get("team"),
                "url": auth_test.get("url"),
            }

            logger.info("Slack service initialized successfully")
            return {
                "success": True,
                "message": "Slack service initialized",
                "bot_user_id": self.bot_user_id,
                "workspace": self.workspace_info,
            }

        except Exception as e:
            logger.error(f"Error initializing Slack service: {str(e)}")
            return {"success": False, "error": str(e)}

    def get_authorization_url(
        self,
        scopes: List[str],
        state: Optional[str] = None,
        redirect_uri: Optional[str] = None,
    ) -> str:
        """Get OAuth2 authorization URL."""
        params = {
            "client_id": self.client_id,
            "scope": ",".join(scopes),
            "redirect_uri": redirect_uri or os.getenv("SLACK_REDIRECT_URI", ""),
        }

        if state:
            params["state"] = state

        return f"{self.auth_url}?{urlencode(params)}"

    async def exchange_code_for_token(self, authorization_code: str) -> Dict[str, Any]:
        """Exchange authorization code for access token."""
        try:
            data = {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "code": authorization_code,
            }

            async with self.session.post(self.oauth_url, data=data) as response:
                if response.status == 200:
                    result = await response.json()

                    if result.get("ok"):
                        return {
                            "success": True,
                            "access_token": result.get("access_token"),
                            "bot_user_id": result.get("bot_user_id"),
                            "scope": result.get("scope"),
                            "team": result.get("team", {}),
                            "authed_user": result.get("authed_user", {}),
                        }
                    else:
                        return {
                            "success": False,
                            "error": result.get("error", "Token exchange failed"),
                        }
                else:
                    return {
                        "success": False,
                        "error": f"HTTP {response.status}: Token exchange failed",
                    }

        except Exception as e:
            logger.error(f"Error exchanging code for token: {str(e)}")
            return {"success": False, "error": str(e)}

    def _get_headers(self) -> Dict[str, str]:
        """Get headers for API requests."""
        return {
            "Authorization": f"Bearer {self.bot_token}",
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

    async def test_auth(self) -> Dict[str, Any]:
        """Test authentication with Slack API."""
        try:
            await self._check_rate_limit()

            headers = self._get_headers()

            async with self.session.post(
                f"{self.api_base_url}/auth.test", headers=headers
            ) as response:
                if response.status == 200:
                    result = await response.json()

                    if result.get("ok"):
                        return {
                            "success": True,
                            "user_id": result.get("user_id"),
                            "team_id": result.get("team_id"),
                            "team": result.get("team"),
                            "url": result.get("url"),
                            "user": result.get("user"),
                        }
                    else:
                        return {
                            "success": False,
                            "error": result.get("error", "Authentication failed"),
                        }
                else:
                    return {
                        "success": False,
                        "error": f"HTTP {response.status}: Authentication test failed",
                    }

        except Exception as e:
            logger.error(f"Error testing authentication: {str(e)}")
            return {"success": False, "error": str(e)}

    async def send_message(
        self,
        channel: str,
        text: str,
        blocks: Optional[List[Dict[str, Any]]] = None,
        thread_ts: Optional[str] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Send message to Slack channel."""
        try:
            await self._check_rate_limit()

            data = {"channel": channel, "text": text}

            if blocks:
                data["blocks"] = blocks

            if thread_ts:
                data["thread_ts"] = thread_ts

            if attachments:
                data["attachments"] = attachments

            headers = self._get_headers()

            async with self.session.post(
                f"{self.api_base_url}/chat.postMessage", headers=headers, json=data
            ) as response:
                if response.status == 200:
                    result = await response.json()

                    if result.get("ok"):
                        return {
                            "success": True,
                            "channel": result.get("channel"),
                            "ts": result.get("ts"),
                            "message": result.get("message", {}),
                        }
                    else:
                        return {
                            "success": False,
                            "error": result.get("error", "Message sending failed"),
                        }
                else:
                    return {
                        "success": False,
                        "error": f"HTTP {response.status}: Message sending failed",
                    }

        except Exception as e:
            logger.error(f"Error sending message: {str(e)}")
            return {"success": False, "error": str(e)}

    async def send_rich_message(
        self,
        channel: str,
        title: str,
        message: str,
        color: str = "good",
        fields: Optional[List[Dict[str, Any]]] = None,
        actions: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Send rich formatted message with attachments."""
        try:
            attachment = {
                "color": color,
                "title": title,
                "text": message,
                "ts": int(datetime.utcnow().timestamp()),
            }

            if fields:
                attachment["fields"] = fields

            if actions:
                attachment["actions"] = actions

            result = await self.send_message(
                channel=channel, text=title, attachments=[attachment]
            )

            return result

        except Exception as e:
            logger.error(f"Error sending rich message: {str(e)}")
            return {"success": False, "error": str(e)}

    async def create_channel(
        self, name: str, is_private: bool = False, purpose: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create Slack channel."""
        try:
            await self._check_rate_limit()

            data = {"name": name, "is_private": is_private}

            headers = self._get_headers()

            async with self.session.post(
                f"{self.api_base_url}/conversations.create", headers=headers, json=data
            ) as response:
                if response.status == 200:
                    result = await response.json()

                    if result.get("ok"):
                        channel_info = result.get("channel", {})

                        # Set channel purpose if provided
                        if purpose and channel_info.get("id"):
                            await self.set_channel_purpose(channel_info["id"], purpose)

                        return {
                            "success": True,
                            "channel_id": channel_info.get("id"),
                            "channel_name": channel_info.get("name"),
                            "channel_info": channel_info,
                        }
                    else:
                        return {
                            "success": False,
                            "error": result.get("error", "Channel creation failed"),
                        }
                else:
                    return {
                        "success": False,
                        "error": f"HTTP {response.status}: Channel creation failed",
                    }

        except Exception as e:
            logger.error(f"Error creating channel: {str(e)}")
            return {"success": False, "error": str(e)}

    async def set_channel_purpose(
        self, channel_id: str, purpose: str
    ) -> Dict[str, Any]:
        """Set channel purpose/description."""
        try:
            await self._check_rate_limit()

            data = {"channel": channel_id, "purpose": purpose}

            headers = self._get_headers()

            async with self.session.post(
                f"{self.api_base_url}/conversations.setPurpose",
                headers=headers,
                json=data,
            ) as response:
                if response.status == 200:
                    result = await response.json()

                    if result.get("ok"):
                        return {"success": True, "purpose": result.get("purpose")}
                    else:
                        return {
                            "success": False,
                            "error": result.get("error", "Setting purpose failed"),
                        }
                else:
                    return {
                        "success": False,
                        "error": f"HTTP {response.status}: Setting purpose failed",
                    }

        except Exception as e:
            logger.error(f"Error setting channel purpose: {str(e)}")
            return {"success": False, "error": str(e)}

    async def invite_users_to_channel(
        self, channel_id: str, user_ids: List[str]
    ) -> Dict[str, Any]:
        """Invite users to channel."""
        try:
            await self._check_rate_limit()

            data = {"channel": channel_id, "users": ",".join(user_ids)}

            headers = self._get_headers()

            async with self.session.post(
                f"{self.api_base_url}/conversations.invite", headers=headers, json=data
            ) as response:
                if response.status == 200:
                    result = await response.json()

                    if result.get("ok"):
                        return {"success": True, "channel": result.get("channel", {})}
                    else:
                        return {
                            "success": False,
                            "error": result.get("error", "Invitation failed"),
                        }
                else:
                    return {
                        "success": False,
                        "error": f"HTTP {response.status}: Invitation failed",
                    }

        except Exception as e:
            logger.error(f"Error inviting users to channel: {str(e)}")
            return {"success": False, "error": str(e)}

    async def upload_file(
        self,
        file_path: str,
        channels: List[str],
        title: Optional[str] = None,
        initial_comment: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Upload file to Slack."""
        try:
            await self._check_rate_limit()

            if not os.path.exists(file_path):
                return {"success": False, "error": "File not found"}

            data = {"channels": ",".join(channels)}

            if title:
                data["title"] = title

            if initial_comment:
                data["initial_comment"] = initial_comment

            headers = {"Authorization": f"Bearer {self.bot_token}"}

            with open(file_path, "rb") as file:
                form_data = aiohttp.FormData()
                form_data.add_field("file", file, filename=os.path.basename(file_path))

                for key, value in data.items():
                    form_data.add_field(key, value)

                async with self.session.post(
                    f"{self.api_base_url}/files.upload", headers=headers, data=form_data
                ) as response:
                    if response.status == 200:
                        result = await response.json()

                        if result.get("ok"):
                            return {"success": True, "file": result.get("file", {})}
                        else:
                            return {
                                "success": False,
                                "error": result.get("error", "File upload failed"),
                            }
                    else:
                        return {
                            "success": False,
                            "error": f"HTTP {response.status}: File upload failed",
                        }

        except Exception as e:
            logger.error(f"Error uploading file: {str(e)}")
            return {"success": False, "error": str(e)}

    async def get_channels(self, types: Optional[str] = None) -> Dict[str, Any]:
        """Get list of channels."""
        try:
            await self._check_rate_limit()

            params = {}
            if types:
                params["types"] = types

            headers = self._get_headers()

            async with self.session.get(
                f"{self.api_base_url}/conversations.list",
                headers=headers,
                params=params,
            ) as response:
                if response.status == 200:
                    result = await response.json()

                    if result.get("ok"):
                        return {"success": True, "channels": result.get("channels", [])}
                    else:
                        return {
                            "success": False,
                            "error": result.get("error", "Getting channels failed"),
                        }
                else:
                    return {
                        "success": False,
                        "error": f"HTTP {response.status}: Getting channels failed",
                    }

        except Exception as e:
            logger.error(f"Error getting channels: {str(e)}")
            return {"success": False, "error": str(e)}

    async def get_users(self) -> Dict[str, Any]:
        """Get list of workspace users."""
        try:
            await self._check_rate_limit()

            headers = self._get_headers()

            async with self.session.get(
                f"{self.api_base_url}/users.list", headers=headers
            ) as response:
                if response.status == 200:
                    result = await response.json()

                    if result.get("ok"):
                        return {"success": True, "members": result.get("members", [])}
                    else:
                        return {
                            "success": False,
                            "error": result.get("error", "Getting users failed"),
                        }
                else:
                    return {
                        "success": False,
                        "error": f"HTTP {response.status}: Getting users failed",
                    }

        except Exception as e:
            logger.error(f"Error getting users: {str(e)}")
            return {"success": False, "error": str(e)}

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check for Slack service."""
        try:
            auth_test = await self.test_auth()

            if auth_test.get("success"):
                return {
                    "status": "healthy",
                    "message": "Slack service is operational",
                    "team": auth_test.get("team"),
                    "last_check": datetime.utcnow().isoformat(),
                }
            else:
                return {
                    "status": "error",
                    "message": "Slack API is not accessible",
                    "error": auth_test.get("error"),
                }

        except Exception as e:
            logger.error(f"Slack health check failed: {str(e)}")
            return {
                "status": "error",
                "message": "Health check failed",
                "error": str(e),
            }

    async def cleanup(self) -> Dict[str, Any]:
        """Cleanup Slack service resources."""
        try:
            if self.session:
                await self.session.close()
                self.session = None

            self.bot_user_id = None
            self.workspace_info = None

            return {
                "status": "success",
                "message": "Slack service cleaned up successfully",
            }

        except Exception as e:
            logger.error(f"Error cleaning up Slack service: {str(e)}")
            return {"status": "error", "error": str(e)}
