# █ █ ▀ █▄▀ ▄▀█ █▀█ ▀    ▄▀█ ▀█▀ ▄▀█ █▀▄▀█ ▄▀█
# █▀█ █ █ █ █▀█ █▀▄ █ ▄  █▀█  █  █▀█ █ ▀ █ █▀█
#
#              © Copyright 2022
#
#          https://t.me/hikariatama
#
# 🔒 Licensed under the GNU GPLv3
# 🌐 https://www.gnu.org/licenses/agpl-3.0.html

# meta developer: @hikariatama

from .. import loader, utils
from telethon import events, types
import logging
import re
import emoji

logger = logging.getLogger(__name__)

# Регулярное выражение для поиска эмодзи в тексте
EMOJI_PATTERN = re.compile(
    "["
    "\U0001F1E0-\U0001F1FF"  # flags (iOS)
    "\U0001F300-\U0001F5FF"  # symbols & pictographs
    "\U0001F600-\U0001F64F"  # emoticons
    "\U0001F680-\U0001F6FF"  # transport & map symbols
    "\U0001F700-\U0001F77F"  # alchemical symbols
    "\U0001F780-\U0001F7FF"  # Geometric Shapes
    "\U0001F800-\U0001F8FF"  # Supplemental Arrows-C
    "\U0001F900-\U0001F9FF"  # Supplemental Symbols and Pictographs
    "\U0001FA00-\U0001FA6F"  # Chess Symbols
    "\U0001FA70-\U0001FAFF"  # Symbols and Pictographs Extended-A
    "\U00002702-\U000027B0"  # Dingbats
    "\U000024C2-\U0001F251"
    "]+"
)

@loader.tds
class AntiRomaMod(loader.Module):
    """Модуль для удаления эмоджи из чата в Telegram"""

    strings = {
        "name": "AntiRoma",
        "banned_anim": "✅ <b>Анимированные эмоджи запрещены в этом чате</b>",
        "unbanned_anim": "✅ <b>Анимированные эмоджи разрешены в этом чате</b>",
        "banned_pack": "✅ <b>Эмоджипак {} запрещен в этом чате</b>",
        "unbanned_pack": "✅ <b>Эмоджипак {} разрешен в этом чате</b>",
        "banned_stick": "✅ <b>Эмоджи {} запрещен в этом чате</b>",
        "unbanned_stick": "✅ <b>Эмоджи {} разрешен в этом чате</b>",
        "all_unbanned": "✅ <b>Все ограничения на эмоджи сняты в этом чате</b>",
        "no_reply": "❌ <b>Ответьте на стикер</b>",
        "debug": "🔄 <b>Обнаружено сообщение с типом: {}</b>",
        "banned_regular": "✅ <b>Обычные эмоджи запрещены в этом чате</b>",
        "unbanned_regular": "✅ <b>Обычные эмоджи разрешены в этом чате</b>",
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            "banned_chats_anim", [], "Список чатов с запретом на анимированные эмоджи",
            "banned_packs", {}, "Словарь запрещенных эмоджипаков по чатам",
            "banned_stickers", {}, "Словарь запрещенных эмоджи по чатам",
            "debug_mode", False, "Режим отладки для диагностики проблем",
            "banned_chats_regular", [], "Список чатов с запретом на обычные эмоджи",
        )

    async def client_ready(self, client, db):
        self.db = db
        self.client = client
        
        # Регистрация обработчика для проверки всех сообщений
        client.add_event_handler(
            self.check_message,
            events.NewMessage()
        )
        
        # Дополнительный обработчик для специфических типов сообщений
        client.add_event_handler(
            self.check_message,
            events.MessageEdited()
        )
    
    async def check_message(self, event):
        try:
            chat_id = utils.get_chat_id(event)
            
            # Режим отладки
            if self.config["debug_mode"]:
                if hasattr(event, "message") and event.message:
                    media_type = type(event.message.media).__name__ if event.message.media else "Нет медиа"
                    await self.client.send_message(
                        chat_id, 
                        self.strings("debug").format(media_type)
                    )
            
            # Проверка на обычные эмодзи в тексте
            if chat_id in self.config["banned_chats_regular"] and hasattr(event, "message") and event.message:
                if event.message.text:
                    # Проверка на наличие эмодзи в тексте
                    if EMOJI_PATTERN.search(event.message.text) or emoji.emoji_count(event.message.text) > 0:
                        await event.delete()
                        return
                
                # Проверка на обычные эмодзи-стикеры
                if event.message.media:
                    if isinstance(event.message.media, types.MessageMediaWebPage):
                        # Проверка на эмодзи в предпросмотре веб-страницы
                        if hasattr(event.message.media.webpage, "title"):
                            if EMOJI_PATTERN.search(event.message.media.webpage.title) or emoji.emoji_count(event.message.media.webpage.title) > 0:
                                await event.delete()
                                return
                    
                    # Проверка на обычные стикеры (не анимированные)
                    if hasattr(event.message.media, "document"):
                        doc = event.message.media.document
                        if hasattr(doc, "mime_type") and doc.mime_type == "image/webp":
                            # Это обычный стикер
                            await event.delete()
                            return
            
            # Проверка на анимированные эмоджи
            if chat_id in self.config["banned_chats_anim"]:
                # Проверка на CustomEmoji (новый тип для эмодзи)
                if hasattr(event, "message") and event.message:
                    # Проверка на наличие CustomEmoji в entities
                    if event.message.entities:
                        for entity in event.message.entities:
                            if isinstance(entity, types.MessageEntityCustomEmoji):
                                await event.delete()
                                return
                    
                    # Проверка на медиа с документом
                    if event.message.media:
                        if hasattr(event.message.media, "document"):
                            doc = event.message.media.document
                            if hasattr(doc, "attributes"):
                                for attr in doc.attributes:
                                    if getattr(attr, "animated", False):
                                        await event.delete()
                                        return
            
            # Проверка на запрещенные эмоджипаки
            if str(chat_id) in self.config["banned_packs"] and event.message and event.message.media:
                if hasattr(event.message.media, "document"):
                    doc = event.message.media.document
                    if hasattr(doc, "attributes"):
                        for attr in doc.attributes:
                            if hasattr(attr, "stickerset") and attr.stickerset:
                                if attr.stickerset.id in self.config["banned_packs"][str(chat_id)]:
                                    await event.delete()
                                    return
            
            # Проверка на запрещенные стикеры
            if str(chat_id) in self.config["banned_stickers"] and event.message and event.message.media:
                if hasattr(event.message.media, "document"):
                    doc = event.message.media.document
                    if doc.id in self.config["banned_stickers"][str(chat_id)]:
                        await event.delete()
                        return
        except Exception as e:
            logger.error(f"Ошибка при проверке сообщения: {e}")
    
    @loader.command(ru_doc="Запретить анимированные эмоджи в этом чате")
    async def bananim(self, message):
        """Ban animated emojis in this chat"""
        chat_id = utils.get_chat_id(message)
        
        if chat_id not in self.config["banned_chats_anim"]:
            self.config["banned_chats_anim"].append(chat_id)
            await utils.answer(message, self.strings("banned_anim"))
        else:
            await utils.answer(message, self.strings("banned_anim"))
    
    @loader.command(ru_doc="Запретить обычные эмоджи в этом чате")
    async def banemoji(self, message):
        """Ban regular emojis in this chat"""
        chat_id = utils.get_chat_id(message)
        
        if chat_id not in self.config["banned_chats_regular"]:
            self.config["banned_chats_regular"].append(chat_id)
            await utils.answer(message, self.strings("banned_regular"))
        else:
            await utils.answer(message, self.strings("banned_regular"))
    
    @loader.command(ru_doc="Разрешить обычные эмоджи в этом чате")
    async def unbanemoji(self, message):
        """Unban regular emojis in this chat"""
        chat_id = utils.get_chat_id(message)
        
        if chat_id in self.config["banned_chats_regular"]:
            self.config["banned_chats_regular"].remove(chat_id)
            await utils.answer(message, self.strings("unbanned_regular"))
        else:
            await utils.answer(message, self.strings("unbanned_regular"))
    
    @loader.command(ru_doc="Включить/выключить режим отладки")
    async def debugmode(self, message):
        """Toggle debug mode for emoji detection"""
        self.config["debug_mode"] = not self.config["debug_mode"]
        status = "включен" if self.config["debug_mode"] else "выключен"
        await utils.answer(message, f"✅ <b>Режим отладки {status}</b>")
    
    @loader.command(ru_doc="Запретить весь эмоджипак в текущем чате")
    async def banpack(self, message):
        """Ban emoji pack in this chat"""
        chat_id = utils.get_chat_id(message)
        reply = await message.get_reply_message()
        
        if not reply or not reply.media:
            await utils.answer(message, self.strings("no_reply"))
            return
        
        if hasattr(reply.media, "document"):
            for attr in reply.media.document.attributes:
                if hasattr(attr, "stickerset") and attr.stickerset:
                    pack_id = attr.stickerset.id
                    pack_name = attr.stickerset.short_name
                    
                    if str(chat_id) not in self.config["banned_packs"]:
                        self.config["banned_packs"][str(chat_id)] = []
                    
                    if pack_id not in self.config["banned_packs"][str(chat_id)]:
                        self.config["banned_packs"][str(chat_id)].append(pack_id)
                    
                    await utils.answer(message, self.strings("banned_pack").format(pack_name))
                    return
        
        await utils.answer(message, self.strings("no_reply"))
    
    @loader.command(ru_doc="Запретить эмоджи в текущем чате")
    async def banstick(self, message):
        """Ban emoji in this chat"""
        chat_id = utils.get_chat_id(message)
        reply = await message.get_reply_message()
        
        if not reply or not reply.media:
            await utils.answer(message, self.strings("no_reply"))
            return
        
        sticker_id = reply.media.document.id
        sticker_emoji = None
        
        for attr in reply.media.document.attributes:
            if hasattr(attr, "alt"):
                sticker_emoji = attr.alt
        
        if str(chat_id) not in self.config["banned_stickers"]:
            self.config["banned_stickers"][str(chat_id)] = []
        
        if sticker_id not in self.config["banned_stickers"][str(chat_id)]:
            self.config["banned_stickers"][str(chat_id)].append(sticker_id)
        
        await utils.answer(message, self.strings("banned_stick").format(sticker_emoji or ""))
    
    @loader.command(ru_doc="Убрать все ограничения в текущем чате")
    async def unbanall(self, message):
        """Remove all emoji restrictions in this chat"""
        chat_id = utils.get_chat_id(message)
        
        # Удаляем из списка запрещенных анимированных эмоджи
        if chat_id in self.config["banned_chats_anim"]:
            self.config["banned_chats_anim"].remove(chat_id)
        
        # Удаляем из списка запрещенных обычных эмоджи
        if chat_id in self.config["banned_chats_regular"]:
            self.config["banned_chats_regular"].remove(chat_id)
        
        # Удаляем из словаря запрещенных паков
        if str(chat_id) in self.config["banned_packs"]:
            del self.config["banned_packs"][str(chat_id)]
        
        # Удаляем из словаря запрещенных стикеров
        if str(chat_id) in self.config["banned_stickers"]:
            del self.config["banned_stickers"][str(chat_id)]
        
        await utils.answer(message, self.strings("all_unbanned"))
    
    @loader.command(ru_doc="Разблокировать анимированные эмоджи в этом чате")
    async def unbananim(self, message):
        """Unban animated emojis in this chat"""
        chat_id = utils.get_chat_id(message)
        
        if chat_id in self.config["banned_chats_anim"]:
            self.config["banned_chats_anim"].remove(chat_id)
        
        await utils.answer(message, self.strings("unbanned_anim"))
    
    @loader.command(ru_doc="Разбанить весь эмоджипак в текущем чате")
    async def unbanpack(self, message):
        """Unban emoji pack in this chat"""
        chat_id = utils.get_chat_id(message)
        reply = await message.get_reply_message()
        
        if not reply or not reply.media:
            await utils.answer(message, self.strings("no_reply"))
            return
        
        if hasattr(reply.media, "document"):
            for attr in reply.media.document.attributes:
                if hasattr(attr, "stickerset") and attr.stickerset:
                    pack_id = attr.stickerset.id
                    pack_name = attr.stickerset.short_name
                    
                    if str(chat_id) in self.config["banned_packs"] and pack_id in self.config["banned_packs"][str(chat_id)]:
                        self.config["banned_packs"][str(chat_id)].remove(pack_id)
                        if not self.config["banned_packs"][str(chat_id)]:
                            del self.config["banned_packs"][str(chat_id)]
                    
                    await utils.answer(message, self.strings("unbanned_pack").format(pack_name))
                    return
        
        await utils.answer(message, self.strings("no_reply"))
    
    @loader.command(ru_doc="Разбанить эмоджи в текущем чате")
    async def unbanstick(self, message):
        """Unban emoji in this chat"""
        chat_id = utils.get_chat_id(message)
        reply = await message.get_reply_message()
        
        if not reply or not reply.media:
            await utils.answer(message, self.strings("no_reply"))
            return
        
        sticker_id = reply.media.document.id
        sticker_emoji = None
        
        for attr in reply.media.document.attributes:
            if hasattr(attr, "alt"):
                sticker_emoji = attr.alt
        
        if str(chat_id) in self.config["banned_stickers"] and sticker_id in self.config["banned_stickers"][str(chat_id)]:
            self.config["banned_stickers"][str(chat_id)].remove(sticker_id)
            if not self.config["banned_stickers"][str(chat_id)]:
                del self.config["banned_stickers"][str(chat_id)]
        
        await utils.answer(message, self.strings("unbanned_stick").format(sticker_emoji or ""))