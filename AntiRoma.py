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

logger = logging.getLogger(__name__)

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
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            "banned_chats_anim", [], "Список чатов с запретом на анимированные эмоджи",
            "banned_packs", {}, "Словарь запрещенных эмоджипаков по чатам",
            "banned_stickers", {}, "Словарь запрещенных эмоджи по чатам",
            "debug_mode", False, "Режим отладки для диагностики проблем",
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