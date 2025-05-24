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
    
    strings = {
        "name": "FreeKeys",
        "enabled": "✅ Модуль FreeKeys включен",
        "disabled": "❌ Модуль FreeKeys выключен",
        "status_enabled": "✅ Статус модуля: Включен",
        "status_disabled": "❌ Статус модуля: Выключен",
        "bot_not_found": "❌ Бот @ExodusLucky_bot не найден",
        "chat_not_found": "❌ Не удалось создать или найти чат KEYS FREE",
        "started": "🔄 Запущена автоматическая проверка призов...",
    }
    
    async def client_ready(self, client, db):
        """Вызывается при загрузке модуля"""
        self._client = client
        self._db = db
        self._bot_id = None
        self._chat_id = None
        self._is_enabled = self._db.get(self.strings["name"], "enabled", False)
        self._handler_added = False
        
        # Попытаемся найти бота по юзернейму
        try:
            bot_entity = await client.get_entity("@ExodusLucky_bot")
            self._bot_id = bot_entity.id
        except Exception as e:
            logger.error(f"Не удалось найти бота: {e}")
        
        # Проверяем существование или создаем новый чат
        await self._ensure_chat_exists()
        
        # Если модуль был включен до перезагрузки, включаем его снова
        if self._is_enabled:
            self._add_handler()
            # Отправляем первую команду /try, если модуль был включен
            await self._send_try()
            
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
    
    def _add_handler(self):
        """Добавляет обработчик сообщений"""
        if not self._handler_added and self._bot_id:
            self._client.add_event_handler(
                self._message_handler,
                types.events.NewMessage(from_users=[self._bot_id])
            )
            self._handler_added = True
            logger.info("Обработчик сообщений добавлен")
    
    def _remove_handler(self):
        """Удаляет обработчик сообщений"""
        if self._handler_added:
            self._client.remove_event_handler(self._message_handler)
            self._handler_added = False
            logger.info("Обработчик сообщений удален")
    
    async def _send_try(self):
        """Отправляет команду /try боту"""
        if self._bot_id and self._is_enabled:
            await self._client.send_message("@ExodusLucky_bot", "/try")
            logger.info("Отправлена команда /try")
    
    @loader.command
    async def keyon(self, message):
        """Включает модуль"""
        if not self._bot_id:
            await utils.answer(message, self.strings["bot_not_found"])
            return
            
        if not self._chat_id:
            await self._ensure_chat_exists()
            if not self._chat_id:
                await utils.answer(message, self.strings["chat_not_found"])
                return
        
        self._is_enabled = True
        self._db.set(self.strings["name"], "enabled", True)
        
        # Добавляем обработчик, если он еще не добавлен
        self._add_handler()
        
        # Отправляем первую команду /try
        await self._send_try()
        
        await utils.answer(message, self.strings["enabled"])
    
    @loader.command
    async def keyoff(self, message):
        """Выключает модуль"""
        self._is_enabled = False
        self._db.set(self.strings["name"], "enabled", False)
        
        # Удаляем обработчик, если он был добавлен
        self._remove_handler()
        
        await utils.answer(message, self.strings["disabled"])
    
    @loader.command
    async def keystatus(self, message):
        """Показывает статус модуля"""
        status = self.strings["status_enabled"] if self._is_enabled else self.strings["status_disabled"]
        chat_status = f"🗣 Чат: {'✅ Найден' if self._chat_id else '❌ Не найден'}"
        bot_status = f"🤖 Бот: {'✅ Найден' if self._bot_id else '❌ Не найден'}"
        handler_status = f"👁 Отслеживание: {'✅ Активно' if self._handler_added else '❌ Не активно'}"
        
        status_text = f"{status}\n\n{bot_status}\n{chat_status}\n{handler_status}"
        
        await utils.answer(message, status_text)
    
    @loader.command
    async def trykey(self, message):
        """Запускает автоматическую проверку на призы"""
        if not self._bot_id:
            await utils.answer(message, self.strings["bot_not_found"])
            return
            
        if not self._chat_id:
            await self._ensure_chat_exists()
            if not self._chat_id:
                await utils.answer(message, self.strings["chat_not_found"])
                return
        
        # Включаем модуль, если он был выключен
        if not self._is_enabled:
            self._is_enabled = True
            self._db.set(self.strings["name"], "enabled", True)
            self._add_handler()
        
        await utils.answer(message, self.strings["started"])
        
        # Отправляем первую команду /try
        await self._send_try()
        
    async def _message_handler(self, event):
        """Обрабатывает сообщения от бота"""
        if not self._is_enabled:
            return
            
        # Проверяем содержимое сообщения
        message_text = event.message.text or ""
        
        # Обработка кнопки для повторной попытки
        if "Доступна новая попытка!" in message_text:
            await asyncio.sleep(1)  # Небольшая задержка
            await self._send_try()
            
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
        self._remove_handler() 