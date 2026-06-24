"""
Websocket wrapper for Discord's Gateway API.
Please note that this is not meant to be used for self-botting and may violate Discord's Terms of Service if used improperly. Use at your own risk.
I made this for educational purposes to learn the Discord Gateway API and to have a simple way to interact with it for my other projects.
"""

import time
import json
import logging
import random
import requests
import websocket
from threading import Thread
from typing import Any, Optional, Union

GATEWAY_URL = "wss://gateway.discord.gg/?v=9&encoding=json"

# Setup logging to see what's happening
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("DiscordWS")

class DiscordWS:
    """WebSocket client for interacting with Discord's Gateway API."""

    def __init__(self, token: str, target_channels: Optional[Union[str, list[str]]] = None, **kwargs) -> None:
        """Initialize the Discord WebSocket client.

        Args:
            token (str): The token used for authentication
            target_channels (str or list[str], optional): A single channel ID or
                list of channel IDs to listen to. If None, listens to all channels.
        """
        self.token: str = token
        self.ws: websocket.WebSocket = websocket.WebSocket()
        self.seq: Optional[int] = None
        self.is_connected: bool = False
        self.session_id: Optional[str] = None
        # If target_channels is a single string, wrap it in a list; otherwise use as provided
        if isinstance(target_channels, str):
            self.target_channels: list = [target_channels]
        else:
            self.target_channels: list = target_channels or []
        self.kwargs = kwargs

    def send_json(self, data: dict[str, Any]) -> None:
        """Sends a JSON payload through the WebSocket connection.
        
        Args:
            data (dict[str, Any]): The data to send as a JSON payload.
        """
        self.ws.send(json.dumps(data))

    def heartbeat(self, interval: float) -> None:
        """Sends periodic pings to keep the connection alive.
        
        Args:
            interval (float): The interval in seconds between heartbeats, as specified by the gateway.
        """
        time.sleep(interval * random.random())
        
        while self.is_connected:
            logger.info("[>] Sending Heartbeat")
            try:
                self.send_json({"op": 1, "d": self.seq})
            except Exception as e:
                logger.error(f"Heartbeat failed: {e}")
                break
            time.sleep(interval)

    def identify(
        self, os: Optional[str] = "Windows",
        browser: Optional[str] = "Chrome",
        device: Optional[str] = "",
        bot: Optional[bool] = False,
        status: Optional[str] = "online",
        activity_name: Optional[str] = None,
        activity_type: int = 0
    ) -> None:
        """Authenticates with the gateway.
        
        Args:
            os (str, optional): The operating system to report. Defaults to "iOS".
            browser (str, optional): The browser to report. Defaults to "Discord iOS".
            device (str, optional): The device to report. Defaults to "iPhone 16 Pro Max".
            bot (bool, optional): Whether to identify as a bot. Defaults to False.
            status (str, optional): Initial status ("online", "dnd", "idle", "invisible"). Defaults to "online".
            activity_name (str, optional): Initial activity name. Defaults to None.
            activity_type (int, optional): Initial activity type. Defaults to 0 (Game).
        """
        logger.info("[*] Sending Identify payload...")
        payload = {
            "op": 2,
            "d": {
                "token": f"{"Bot " if bot else ""}{self.token}",
                "properties": {
                    "os": os,
                    "browser": browser,
                    "device": device
                },
                "presence": {
                    "status": status,
                    "since": 0,
                    "activities": [{"name": activity_name, "type": activity_type}] if activity_name else [],
                    "afk": False
                }
            }
        }
        self.send_json(payload)

    def change_status(self, status: str = "online", activity_name: Optional[str] = None, activity_type: int = 0) -> None:
        """Changes the presence/status of the user.
        
        Args:
            status (str): The new status ("online", "dnd", "idle", "invisible"). Defaults to "online".
            activity_name (str, optional): The new activity name. Defaults to None.
            activity_type (int, optional): The activity type (0=Game, 1=Streaming, 2=Listening, 3=Watching, 4=Custom, 5=Competing). Defaults to 0.
        """
        logger.info(f"[*] Changing status to {status}...")
        payload = {
            "op": 3,
            "d": {
                "since": 0 if status == "idle" else None,
                "activities": [{"name": activity_name, "type": activity_type}] if activity_name else [],
                "status": status,
                "afk": status == "idle"
            }
        }
        self.send_json(payload)

    def start(self, run_forever: bool = True) -> None:
        """Initializes the connection and starts threads.
        
        Args:
            run_forever (bool, optional): If True, the listen method will block and run indefinitely. If False, it will run in a background thread. Defaults to True.
        """
        logger.info(f"[*] Connecting to {GATEWAY_URL}")
        try:
            self.ws.connect(GATEWAY_URL)
            self.is_connected = True

            # handle Hello (Opcode 10) to get heartbeat interval
            hello_packet = json.loads(self.ws.recv())
            heartbeat_interval = hello_packet['d']['heartbeat_interval'] / 1000

            # Heartbeat Thread
            Thread(target=self.heartbeat, args=(heartbeat_interval,), daemon=True).start()

            self.identify()

            # Start Listening for Events
            if run_forever:
                self.listen()
            else:
                # Run the listener in the background
                Thread(target=self.listen, daemon=True).start()

        except Exception as e:
            logger.error(f"Connection error: {e}")
            self.is_connected = False

    def listen(self) -> None:
        """Listens for and processes incoming gateway events."""
        while self.is_connected:
            try:
                response = self.ws.recv()
                if not response:
                    continue
                
                data = json.loads(response)
                
                # Update sequence number for next heartbeat
                if data.get('s') is not None:
                    self.seq = data['s']

                op = data.get('op')
                event_type = data.get('t')

                if op == 0:
                    if event_type == "READY":
                        self.session_id = data['d']['session_id']
                        logger.info(f"[!] Logged in as: {data['d']['user']['username']}")
                    
                    if event_type == "MESSAGE_CREATE":
                        msg_data = data['d']
                        channel_id = msg_data.get('channel_id')

                        # Only process if no target is set, or if the channel matches our list
                        if not self.target_channels or channel_id in self.target_channels:
                            content = msg_data.get('content')
                            author = msg_data.get('author', {}).get('username')
                            logger.info(f"[MSG] #{channel_id} | {author}: {content}")

                elif op == 11:
                    logger.info("[<] Heartbeat ACK received")

            except websocket.WebSocketConnectionClosedException:
                logger.warning("WebSocket connection closed by server. Auto reconnecting")
                self.is_connected = False
                self.start(run_forever=False)

            except Exception as e:
                logger.error(f"Listen error: {e}")
                self.is_connected = False

    def raw(self, message_id: Union[str, int], channel_id: Union[str, int] = None, user_id: Union[str, int] = None) -> dict:
        """Gets the raw message data of a message.

        Args:
            message_id (str | int): The message ID the fetch.
            channel_id (str | int): The channel ID the message was in.
            user_id (str | int): Used instead of channel_id if you do not know the channel ID.

        Returns:
            dict: The raw JSON.
        """
        headers = {"Authorization": self.token, "Content-Type": "application/json"}

        if not channel_id and user_id:
            url = "https://discord.com/api/v9/users/@me/channels"
            payload = {"recipient_id": str(user_id)}
            
            resp = requests.post(url, headers=headers, json=payload)
            
            if 200 <= resp.status_code < 300:
                channel_id = resp.json().get('id')
                return self.raw(message_id, channel_id)
            else:
                logger.warning(f"[!] Could not resolve DM channel for User {user_id}: {resp.status_code}")
                return None

        if channel_id:
            url = f"https://discord.com/api/v9/channels/{channel_id}/messages/{message_id}"
            resp = requests.get(url, headers=headers)
            
            if 200 <= resp.status_code < 300:
                return resp.json()
            else:
                logger.error(f"[!] Failed to fetch message: {resp.status_code}")
                return None

        logger.error("[!] You must provide either a channel_id or a user_id.")
        return None

    def subscribe_to_channel(self, guild_id: Union[str, int], channel_id: Union[str, int]) -> None:
        """Subscribe to a guild channel stream in the gateway.

        Args:
            guild_id (str | int): Guild snowflake that owns the channel.
            channel_id (str | int): Channel snowflake to subscribe to.
        """
        logger.info(f"[*] Subscribing to channel {channel_id} in guild {guild_id}...")
        payload = {
            "op": 14,
            "d": {
                "guild_id": guild_id,
                "typing": True,
                "threads": False,
                "activities": True,
                "members": [],
                "channels": {
                    str(channel_id): [[0, 99]]
                }
            }
        }
        self.send_json(payload)

    def send_message(
        self,
        channel_id: Union[str, int],
        content: str,
        message_id: Optional[Union[str, int]] = None
    ) -> bool:
        """Send a message to a channel via Discord REST API.
        
        This INCLUDES DM groups, as they are technically channels. For DMs, use send_dm().

        Args:
            channel_id (str | int): Target channel snowflake.
            content (str): Message content.
            message_id (str | int, optional): Message snowflake to reply to.

        Returns:
            bool: True if the API accepted the message, else False.
        """
        url = f"https://discord.com/api/v9/channels/{channel_id}/messages"
        headers = {
            "Authorization": self.token,
            "Content-Type": "application/json"
        }
        payload = {"content": content}
        if message_id:
            payload["message_reference"] = {"message_id": message_id, "channel_id": channel_id}
        try:
            response = requests.post(url, headers=headers, json=payload)
            if 199 < response.status_code < 300:
                logger.info(f"[SUCCESS] Message sent to channel {channel_id}")
                return True
            else:
                logger.error(f"[ERROR] Failed to send message: {response.status_code} - {response.text}")
        except Exception as e:
            logger.error(f"Request error: {e}")
        return False

    def send_dm(self, user_id: Union[str, int], content: str) -> bool:
        """Send a direct message to a user.

        This does not include DM groups.

        Args:
            user_id (str | int): Recipient user snowflake.
            content (str): DM content.

        Returns:
            bool: True if the DM channel is created and message is sent, else False.
        """
        url = "https://discord.com/api/v9/users/@me/channels"
        headers = {
            "Authorization": self.token,
            "Content-Type": "application/json"
        }
        payload = {"recipient_id": user_id}

        try:
            response = requests.post(url, headers=headers, json=payload)
            if response.status_code == 200:
                dm_channel_id = response.json().get('id')
                if not dm_channel_id:
                    logger.error("[ERROR] DM channel response missing channel ID")
                    return False
                return self.send_message(dm_channel_id, content)
            else:
                logger.error(f"[ERROR] Failed to create DM channel: {response.status_code} - {response.text}")
        except Exception as e:
            logger.error(f"Request error: {e}")
        return False

    def click(
        self,
        application_id: Union[str, int],
        channel_id: Union[str, int],
        message_id: Union[str, int],
        custom_id: str,
        guild_id: Optional[Union[str, int]] = None
    ) -> bool:
        """Simulate a button click by sending an interaction payload.

        Args:
            application_id (str | int): Application snowflake that owns the component.
            channel_id (str | int): Channel snowflake containing the message.
            message_id (str | int): Message snowflake containing the component.
            custom_id (str): Component custom ID to click.
            guild_id (str | int, optional): Guild snowflake, if the message is in a guild.

        Returns:
            bool: True if interaction is accepted, else False.
        """
        url = "https://discord.com/api/v9/interactions"
        headers = {
            "Authorization": self.token,
            "Content-Type": "application/json"
        }
        payload = {
            "type": 3,
            "application_id": application_id,
            "guild_id": guild_id,
            "channel_id": channel_id,
            "message_id": message_id,
            "session_id": self.session_id,
            "data": {
                "component_type": 2,
                "custom_id": custom_id
            },
        }

        try:
            response = requests.post(url, headers=headers, json=payload)
            if 199 < response.status_code < 300:
                logger.info(f"[SUCCESS] Button with custom_id '{custom_id}' clicked in channel {channel_id}")
                return True
            else:
                logger.error(f"[ERROR] Failed to click button: {response.status_code} - {response.text}")
        except Exception as e:
            logger.error(f"Request error: {e}")
        return False

    def command(
        self,
        application_id: Union[str, int],
        channel_id: Union[str, int],
        command_id: Union[str, int],
        command_name: str,
        version: Union[str, int],
        options: Optional[list[dict[str, Any]]] = None,
        guild_id: Optional[Union[str, int]] = None
    ) -> bool:
        """Simulate a slash command by sending an interaction payload.

        Args:
            application_id (str | int): Application snowflake for the command.
            channel_id (str | int): Channel snowflake where command runs.
            command_id (str | int): Command snowflake.
            command_name (str): Slash command name without leading slash.
            version (str | int): Command version from Discord.
            options (list[dict[str, Any]], optional): Command options payload.
            guild_id (str | int, optional): Guild snowflake, if guild scoped.

        Returns:
            bool: True if interaction is accepted, else False.
        """
        url = "https://discord.com/api/v9/interactions"
        headers = {
            "Authorization": self.token,
            "Content-Type": "application/json"
        }
        
        # Discord requires a nonce for user commands (a unique timestamp identifier)
        nonce = str(int(time.time() * 1000 - 1420070400000) << 22)

        payload = {
            "type": 2, # 2 = APPLICATION_COMMAND
            "application_id": application_id,
            "guild_id": guild_id,
            "channel_id": channel_id,
            "session_id": self.session_id,
            "nonce": nonce,
            "data": {
                "version": version,
                "id": command_id,
                "name": command_name,
                "type": 1,             # 1 = CHAT_INPUT (Slash Command)
                "options": options or [],
                "application_command": {
                    "id": command_id,
                    "application_id": application_id,
                    "version": version,
                    "default_member_permissions": None,
                    "type": 1,
                    "nsfw": False,
                    "name": command_name,
                    "description": "", 
                    "dm_permission": True,
                    "contexts": None
                }
            },
        }

        try:
            response = requests.post(url, headers=headers, json=payload)
            if 199 < response.status_code < 300:
                logger.info(f"[SUCCESS] Command '/{command_name}' executed in channel {channel_id}")
                return True
            else:
                logger.error(f"[ERROR] Failed to execute command: {response.status_code} - {response.text}")
        except Exception as e:
            logger.error(f"Request error: {e}")
        return False

    def get_servers(self) -> Optional[list[dict[str, Any]]]:
        """Fetches the list of guilds the user is in via REST API.

        Returns:
            list[dict[str, Any]]: List of guild objects if successful, else None.
        """
        url = "https://discord.com/api/v9/users/@me/guilds"
        headers = {"Authorization": self.token}
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"[ERROR] Failed to fetch guilds: {response.status_code} - {response.text}")
        except Exception as e:
            logger.error(f"Request error: {e}")
        return None

    def close(self) -> None:
        """Closes the WebSocket connection."""
        self.is_connected = False
        self.ws.close()

if __name__ == "__main__":
    pass