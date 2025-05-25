# █▀▄▀█ █▀▀ █▀▄ █ ▄▀█ █▀▀ █ █   ▀█▀ █▀▀ █▀█ █ █▄▀ █▄▀ ▄▀█
# █░▀░█ ██▄ █▄▀ █ █▀█ █▀░ █ █▄▄ ░█░ ██▄ █▀▄ █ █░█ █░█ █▀█

# meta developer: @MeccCZ

from telethon import events
from telethon.tl.types import Message, MessageMediaPhoto, MessageMediaDocument
import re
import langdetect

from .. import loader, utils


@loader.tds
class MediaFilterIkkaMod(loader.Module):
    """
    Автоматически удаляет медиа и не-русские сообщения
    в выбранных чатах от собеседника
    """
    
    strings = {
        "name": "MediaFilterIkka",
        "enabled": "✅ MediaFilterIkka активирован в этом чате",
        "disabled": "❌ MediaFilterIkka деактивирован в этом чате",
        "config_caption": "Настройки MediaFilterIkka",
        "filter_media": "Фильтровать медиа",
        "filter_non_russian": "Фильтровать не-русские сообщения",
    }
    
    strings_ru = {
        "enabled": "✅ MediaFilterIkka активирован в этом чате",
        "disabled": "❌ MediaFilterIkka деактивирован в этом чате",
        "config_caption": "Настройки MediaFilterIkka",
        "filter_media": "Фильтровать медиа",
        "filter_non_russian": "Фильтровать не-русские сообщения",
    }
    
    def __init__(self):
        self.config = loader.ModuleConfig(
            "filter_media", True, lambda: self.strings("filter_media"),
            "filter_non_russian", True, lambda: self.strings("filter_non_russian"),
        )
        self.active_chats = set()
    
    async def client_ready(self, client, db):
        self._client = client
        self._db = db
        # Восстанавливаем активные чаты из БД
        self.active_chats = set(self.get("active_chats", []))
    
    @loader.command(
        ru_doc="Переключить фильтрацию медиа и не-русских сообщений в текущем чате"
    )
    async def mfiltercmd(self, message: Message):
        """Toggle media filtering in the current chat"""
        chat_id = utils.get_chat_id(message)
        
        if chat_id in self.active_chats:
            self.active_chats.remove(chat_id)
            await utils.answer(message, self.strings("disabled"))
        else:
            self.active_chats.add(chat_id)
            await utils.answer(message, self.strings("enabled"))
        
        # Сохраняем состояние в БД
        self.set("active_chats", list(self.active_chats))
    
    @loader.watcher()
    async def watcher(self, message: Message):
        # Проверяем, активирован ли модуль в этом чате
        chat_id = utils.get_chat_id(message)
        if chat_id not in self.active_chats:
            return
        
        # Игнорируем свои сообщения
        if message.sender_id == self._client.tg_id:
            return
        
        # Проверяем, является ли сообщение медиа
        if self.config["filter_media"] and self._is_media(message):
            await message.delete()
            return
        
        # Проверяем язык сообщения, если есть текст
        if self.config["filter_non_russian"] and message.text:
            try:
                lang = langdetect.detect(message.text)
                if lang != "ru":
                    await message.delete()
                    return
            except langdetect.lang_detect_exception.LangDetectException:
                # В случае ошибки определения языка (напр., для коротких сообщений) - пропускаем
                pass
    
    def _is_media(self, message: Message) -> bool:
        """Check if the message contains media to be filtered"""
        if not hasattr(message, "media"):
            return False
            
        # Проверяем типы медиа
        if isinstance(message.media, MessageMediaPhoto):
            return True  # Фото
            
        if isinstance(message.media, MessageMediaDocument):
            # Проверяем MIME-типы для определения видео, GIF, стикеров и файлов
            if not hasattr(message.media.document, "mime_type"):
                return False
                
            mime_type = message.media.document.mime_type
            
            # Видео
            if mime_type.startswith("video/"):
                return True
                
            # GIF
            if mime_type == "image/gif":
                return True
                
            # Стикеры
            if mime_type == "application/x-tgsticker":
                return True
                
            # Эмодзи (и анимированные эмодзи)
            if mime_type == "application/x-tgsdice":
                return True
                
            # Любые другие файлы
            return True
            
        # Анимированные эмодзи и другие специальные типы
        return message.media is not None