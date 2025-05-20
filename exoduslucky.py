# 
# █▀▀ ▀▄▀ █▀█ █▀▄ █░█ █▀ █░░ █░█ █▀▀ █▄▀ █▄█
# ██▄ █░█ █▄█ █▄▀ █▄█ ▄█ █▄▄ █▄█ █▄▄ █░█ ░█░
# 
# Модуль для автоматической отправки команды /try в @ExodusLucky_bot
# Модуль анализирует ответ бота и ждет указанное время + 1 минута
#
# Разработчик: @MeccCZ

import asyncio
import logging
import re
from telethon import events

from .. import loader, utils

logger = logging.getLogger(__name__)

@loader.tds
class ExodusLuckyMod(loader.Module):
    """Автоматически отправляет команду /try боту @ExodusLucky_bot с интеллектуальной задержкой"""
    
    strings = {
        "name": "ExodusLucky",
        "started": "✅ Автоматическая отправка команды /try боту @ExodusLucky_bot активирована",
        "stopped": "🛑 Автоматическая отправка команды /try остановлена",
        "status_on": "✅ Статус: активно (ожидание ответа бота + 1 минута)",
        "status_off": "🛑 Статус: не активно",
        "already_running": "⚠️ Автоотправка уже запущена",
        "not_running": "⚠️ Автоотправка не запущена",
        "waiting": "⏳ Ожидание: {wait_time} минут",
    }
    
    def __init__(self):
        self.config = loader.ModuleConfig(
            "DEFAULT_INTERVAL", 11, "Интервал отправки в минутах (если не удалось определить из ответа)",
            "ADDITIONAL_MINUTES", 1, "Дополнительное время ожидания в минутах",
        )
        self.task = None
        self.bot_username = "ExodusLucky_bot"
        self._bot_id = None
        self._waiting_event = None
        self._next_wait_time = None
    
    async def client_ready(self, client, db):
        """Вызывается при готовности клиента"""
        self.client = client
        self.db = db
        self._running = False
        self._waiting_event = asyncio.Event()
        
        # Получаем ID бота для фильтрации сообщений
        try:
            bot_entity = await self.client.get_entity(self.bot_username)
            self._bot_id = bot_entity.id
            
            # Регистрируем обработчик сообщений от бота
            self.client.add_event_handler(
                self._handle_bot_response,
                events.NewMessage(from_users=self._bot_id)
            )
        except Exception as e:
            logger.error(f"Ошибка при инициализации модуля: {str(e)}")
    
    async def _handle_bot_response(self, event):
        """Обрабатывает ответы от бота"""
        if not self._running:
            return
            
        try:
            message_text = event.message.text
            
            # Ищем упоминание о времени ожидания
            wait_time_match = re.search(r'через (\d+) минут', message_text)
            if wait_time_match:
                wait_minutes = int(wait_time_match.group(1))
                # Добавляем дополнительную минуту
                self._next_wait_time = wait_minutes + self.config["ADDITIONAL_MINUTES"]
                logger.info(f"Обнаружено время ожидания: {wait_minutes} минут, следующая попытка через {self._next_wait_time} минут")
                
                # Уведомление о следующем времени ожидания
                await self.client.send_message(
                    "me",
                    self.strings["waiting"].format(wait_time=self._next_wait_time)
                )
                
                # Сигнализируем основному циклу, что время ожидания определено
                self._waiting_event.set()
        except Exception as e:
            logger.error(f"Ошибка при обработке сообщения от бота: {str(e)}")
    
    async def get_bot_entity(self):
        """Получает Entity бота"""
        return await self.client.get_entity(self.bot_username)
    
    async def exoduslucky_loop(self):
        """Основной цикл отправки сообщений"""
        try:
            bot_entity = await self.get_bot_entity()
            default_interval = self.config["DEFAULT_INTERVAL"] * 60
            
            while self._running:
                try:
                    # Сбрасываем событие перед отправкой команды
                    self._waiting_event.clear()
                    self._next_wait_time = None
                    
                    # Отправляем команду
                    await self.client.send_message(bot_entity, "/try")
                    logger.info(f"Команда /try отправлена боту {self.bot_username}")
                    
                    # Ждем обработки ответа ботом (максимум 10 секунд)
                    try:
                        await asyncio.wait_for(self._waiting_event.wait(), timeout=10)
                    except asyncio.TimeoutError:
                        logger.warning("Тайм-аут ожидания ответа от бота, используем стандартный интервал")
                    
                    # Определяем время ожидания
                    wait_seconds = (self._next_wait_time * 60) if self._next_wait_time else default_interval
                    logger.info(f"Ожидание {wait_seconds/60} минут до следующей попытки")
                    
                    # Ждем указанное время
                    await asyncio.sleep(wait_seconds)
                    
                except Exception as e:
                    logger.error(f"Ошибка при отправке сообщения: {str(e)}")
                    await asyncio.sleep(default_interval)
        
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
            status_text = self.strings["status_on"]
            if self._next_wait_time:
                status_text += f"\n⏳ Следующая попытка: через {self._next_wait_time} минут"
            await utils.answer(message, status_text)
        else:
            await utils.answer(message, self.strings["status_off"]) 