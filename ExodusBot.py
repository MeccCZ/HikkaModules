"""
    ExodusBot - Hikka userbot module for interacting with ExodusLucky_bot
    This module sends the /try command to @ExodusLucky_bot and forwards
    messages containing specific keywords to a dedicated chat.
"""

# requires: hikka

from .. import loader, utils
import asyncio
import logging
from telethon import types

logger = logging.getLogger(__name__)

@loader.tds
class ExodusBotMod(loader.Module):
    """Module to interact with @ExodusLucky_bot and forward winning messages"""
    
    strings = {
        "name": "ExodusBot",
        "enabled": "📱 ExodusBot module is now enabled",
        "disabled": "📴 ExodusBot module is now disabled",
        "status": "⚙️ ExodusBot module is currently {status}",
        "already_enabled": "⚠️ ExodusBot module is already enabled",
        "already_disabled": "⚠️ ExodusBot module is already disabled",
        "forwarded": "✅ Message forwarded to KEYS FREE chat",
        "chat_created": "🔑 Created chat 'KEYS FREE' for storing winning messages",
        "try_sent": "🎮 Sent /try command to @ExodusLucky_bot"
    }
    
    async def client_ready(self, client, db):
        """Called when client is ready"""
        self.client = client
        self.db = db
        self.bot_id = None
        self.first_try_sent = False
        self.keys_chat = None
        self.config = {
            "enabled": False,
            "keywords": ["Поздравляем", "Системный джекпот"]
        }
        
        # Load config from database
        if self.get("config"):
            self.config.update(self.get("config"))
        
        # Find bot ID
        try:
            bot_entity = await self.client.get_entity("@ExodusLucky_bot")
            self.bot_id = bot_entity.id
            logger.info(f"ExodusLucky_bot ID: {self.bot_id}")
        except Exception as e:
            logger.error(f"Failed to get ExodusLucky_bot entity: {e}")
            
        # Create keys chat if not exists
        if self.config["enabled"]:
            await self._ensure_keys_chat_exists()
    
    async def _ensure_keys_chat_exists(self):
        """Ensures that the KEYS FREE chat exists"""
        dialogs = await self.client.get_dialogs()
        for dialog in dialogs:
            if dialog.name == "KEYS FREE":
                self.keys_chat = dialog.entity.id
                return
        
        # Create chat if not found
        try:
            result = await self.client(types.messages.CreateChatRequest(
                users=["me"],
                title="KEYS FREE"
            ))
            self.keys_chat = result.chats[0].id
            await self.client.send_message(
                self.keys_chat,
                "🔑 This chat was created to store winning messages from @ExodusLucky_bot"
            )
            self.set("keys_chat_id", self.keys_chat)
            await utils.answer(self, self.strings["chat_created"])
        except Exception as e:
            logger.error(f"Failed to create KEYS FREE chat: {e}")
    
    def get(self, key, default=None):
        """Get value from database"""
        return self.db.get(self.strings["name"], key, default)
    
    def set(self, key, value):
        """Set value in database"""
        self.db.set(self.strings["name"], key, value)
        
    async def exodusenablecmd(self, message):
        """Enable ExodusBot module"""
        if self.config["enabled"]:
            return await utils.answer(message, self.strings["already_enabled"])
        
        self.config["enabled"] = True
        self.set("config", self.config)
        
        await self._ensure_keys_chat_exists()
        
        # Send first /try command
        if not self.first_try_sent and self.bot_id:
            await self.client.send_message(self.bot_id, "/try")
            self.first_try_sent = True
            logger.info("Sent first /try command to @ExodusLucky_bot")
            
        return await utils.answer(message, self.strings["enabled"])
    
    async def exodusdisablecmd(self, message):
        """Disable ExodusBot module"""
        if not self.config["enabled"]:
            return await utils.answer(message, self.strings["already_disabled"])
        
        self.config["enabled"] = False
        self.set("config", self.config)
        return await utils.answer(message, self.strings["disabled"])
    
    async def exodusstatuscmd(self, message):
        """Check ExodusBot module status"""
        status = "enabled" if self.config["enabled"] else "disabled"
        return await utils.answer(
            message, 
            self.strings["status"].format(status=status)
        )
        
    @loader.watcher()
    async def watcher(self, message):
        """Watch for messages from ExodusLucky_bot"""
        if not self.config["enabled"]:
            return
            
        # Check if message is from ExodusLucky_bot
        if not message.sender_id == self.bot_id:
            return
            
        # Send first /try command if not sent yet
        if not self.first_try_sent:
            await self.client.send_message(self.bot_id, "/try")
            self.first_try_sent = True
            await message.client.send_message(
                message.chat_id,
                self.strings["try_sent"]
            )
            return
            
        # Check for trigger message (Available new attempt)
        if "Доступна новая попытка" in message.text and "/try" in message.text:
            await asyncio.sleep(1)  # Small delay
            await self.client.send_message(self.bot_id, "/try")
            logger.info("Sent /try command to @ExodusLucky_bot")
            return
            
        # Check for keywords in message text
        if any(keyword in message.text for keyword in self.config["keywords"]):
            # Ensure keys chat exists
            await self._ensure_keys_chat_exists()
            
            # Forward message to keys chat
            await self.client.forward_messages(
                self.keys_chat,
                message
            )
            logger.info(f"Forwarded winning message to KEYS FREE chat") 