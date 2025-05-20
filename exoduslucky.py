# 
# █▀▀ ▀▄▀ █▀█ █▀▄ █░█ █▀ █░░ █░█ █▀▀ █▄▀ █▄█
# ██▄ █░█ █▄█ █▄▀ █▄█ ▄█ █▄▄ █▄█ █▄▄ █░█ ░█░
# 
# Модуль для автоматической отправки команды /try в @ExodusLucky_bot
# Интервал: 11 минут
#
# Разработчик: @antml

import asyncio
import logging
from telethon.tl.functions.messages import GetPeerDialogsRequest

from .. import loader, utils

logger = logging.getLogger(__name__)

@loader.tds
class ExodusLuckyMod(loader.Module):
    """Автоматически отправляет команду /try боту @ExodusLucky_bot с заданным интервалом"""
    
    strings = {
        "name": "ExodusLucky",
        "started": "✅ Автоматическая отправка команды /try боту @ExodusLucky_bot активирована",
        "stopped": "🛑 Автоматическая отправка команды /try остановлена",
        "status_on": "✅ Статус: активно (интервал 11 минут)",
        "status_off": "🛑 Статус: не активно",
        "already_running": "⚠️ Автоотправка уже запущена",
        "not_running": "⚠️ Автоотправка не запущена",
    }
    
    def __init__(self):
        self.config = loader.ModuleConfig(
            "INTERVAL", 11, "Интервал отправки в минутах",
        )
        self.task = None
        self.bot_username = "ExodusLucky_bot"
    
    async def client_ready(self, client, db):
        """Вызывается при готовности клиента"""
        self.client = client
        self.db = db
        self._running = False
    
    async def get_bot_entity(self):
        """Получает Entity бота"""
        return await self.client.get_entity(self.bot_username)
    
    async def exoduslucky_loop(self):
        """Основной цикл отправки сообщений"""
        try:
            bot_entity = await self.get_bot_entity()
            interval_seconds = self.config["INTERVAL"] * 60
            
            while self._running:
                try:
                    await self.client.send_message(bot_entity, "/try")
                    logger.info(f"Команда /try отправлена боту {self.bot_username}")
                except Exception as e:
                    logger.error(f"Ошибка при отправке сообщения: {str(e)}")
                
                await asyncio.sleep(interval_seconds)
        
        except Exception as e:
            logger.error(f"Ошибка в цикле exoduslucky_loop: {str(e)}")
            self._running = False
    
    async def exluckyoncmd(self, message):
        """Запускает автоматическую отправку"""
        if self._running:
            return await utils.answer(message, self.strings["already_running"])
        
        self._running = True
        self.task = asyncio.create_task(self.exoduslucky_loop())
        await utils.answer(message, self.strings["started"])
    
    async def exluckyoffcmd(self, message):
        """Останавливает автоматическую отправку"""
        if not self._running:
            return await utils.answer(message, self.strings["not_running"])
        
        self._running = False
        if self.task and not self.task.cancelled():
            self.task.cancel()
        
        await utils.answer(message, self.strings["stopped"])
    
    async def exluckystatuscmd(self, message):
        """Показывает статус автоматической отправки"""
        if self._running:
            await utils.answer(message, self.strings["status_on"])
        else:
            await utils.answer(message, self.strings["status_off"]) 