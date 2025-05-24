import asyncio
import logging
from telethon import types
from telethon.tl.functions.messages import CreateChatRequest
from telethon.tl.functions.channels import InviteToChannelRequest
from .. import loader, utils

logger = logging.getLogger(__name__)

@loader.tds
class FreeKeysMod(loader.Module):
    """Автоматически отправляет /try боту @ExodusLucky_bot и перенаправляет важные сообщения в специальный чат"""
    
    strings = {"name": "FreeKeys"}
    
    async def client_ready(self, client, db):
        """Вызывается при загрузке модуля"""
        self._client = client
        self._db = db
        self._bot_id = None
        self._chat_id = None
        
        # Попытаемся найти бота по юзернейму
        try:
            bot_entity = await client.get_entity("@ExodusLucky_bot")
            self._bot_id = bot_entity.id
        except Exception as e:
            logger.error(f"Не удалось найти бота: {e}")
        
        # Проверяем существование или создаем новый чат
        await self._ensure_chat_exists()
            
    async def _ensure_chat_exists(self):
        """Проверяет существование чата или создает новый"""
        for dialog in await self._client.get_dialogs():
            if dialog.title == "KEYS FREE":
                self._chat_id = dialog.entity.id
                return
                
        # Создаем новый чат, если он не существует
        try:
            result = await self._client(CreateChatRequest(
                users=["me"],
                title="KEYS FREE"
            ))
            self._chat_id = result.chats[0].id
            logger.info(f"Создан новый чат KEYS FREE с ID {self._chat_id}")
        except Exception as e:
            logger.error(f"Не удалось создать чат: {e}")
    
    @loader.command
    async def trykey(self, message):
        """Запускает автоматическую проверку на призы"""
        if not self._bot_id:
            await utils.answer(message, "❌ Бот @ExodusLucky_bot не найден")
            return
            
        if not self._chat_id:
            await self._ensure_chat_exists()
            if not self._chat_id:
                await utils.answer(message, "❌ Не удалось создать или найти чат KEYS FREE")
                return
        
        await utils.answer(message, "🔄 Запущена автоматическая проверка призов...")
        
        # Отправляем первую команду /try
        await self._client.send_message("@ExodusLucky_bot", "/try")
        
        # Устанавливаем обработчик для мониторинга сообщений
        self._client.add_event_handler(
            self._message_handler,
            types.events.NewMessage(from_users=[self._bot_id])
        )
        
    async def _message_handler(self, event):
        """Обрабатывает сообщения от бота"""
        # Проверяем содержимое сообщения
        message_text = event.message.text or ""
        
        # Обработка кнопки для повторной попытки
        if "Доступна новая попытка!" in message_text:
            await asyncio.sleep(1)  # Небольшая задержка
            await self._client.send_message("@ExodusLucky_bot", "/try")
            
        # Проверка на выигрыш
        if "Поздравляем" in message_text or "Системный джекпот" in message_text:
            # Пересылаем сообщение в специальный чат
            try:
                await self._client.forward_messages(
                    entity=self._chat_id,
                    messages=[event.message]
                )
                logger.info("✅ Обнаружен выигрыш! Сообщение переслано в чат KEYS FREE")
            except Exception as e:
                logger.error(f"Ошибка при пересылке сообщения: {e}")
            
    async def on_unload(self):
        """Вызывается при выгрузке модуля"""
        # Удаляем обработчик при выгрузке модуля
        self._client.remove_event_handler(self._message_handler) 