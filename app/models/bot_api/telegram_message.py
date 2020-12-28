#!/usr/bin/env python
# pylint: disable=too-many-branches,too-many-statements,unsubscriptable-object
#
# A lightweight Telegram Bot running on Flask
#
# Copyright 2020 Rodion Nehoroshev <rodion.nehoroshev@gmail.com>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Telegram message data model"""
import re
from collections import OrderedDict
from datetime import datetime
from operator import attrgetter
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy.orm import foreign
from sqlalchemy.sql import and_

from common.db import BaseModel, BigIntegerType, PersistableMixin, db

if TYPE_CHECKING:
    from .telegram_bot import TelegramBot  # noqa: F401
    from .telegram_chat import TelegramChat  # noqa: F401
    from .telegram_message_entity import TelegramMessageEntity  # noqa: F401
    from .telegram_user import TelegramUser  # noqa: F401


class TelegramMessage(BaseModel, PersistableMixin):
    """Message object model from Telegram Bot API

    https://core.telegram.org/bots/api#message
    This object represents a message.
    """

    __tablename__ = "telegram_message"

    # A bot that received message
    bot_id = db.Column(
        BigIntegerType,
        db.ForeignKey("telegram_bot.user_id"),
        primary_key=True,
        autoincrement=False,
    )
    bot = db.relationship("TelegramBot", back_populates="messages")

    # A chat message was sent to
    chat_id = db.Column(
        BigIntegerType, db.ForeignKey("telegram_chat.id"), primary_key=True, autoincrement=False
    )
    chat = db.relationship("TelegramChat", back_populates="messages")

    # Message ID
    message_id = db.Column(BigIntegerType, primary_key=True, autoincrement=False)

    # Optional. Sender, empty for messages sent to channels
    from_user_id = db.Column(
        BigIntegerType, db.ForeignKey("telegram_user.id"), index=True, nullable=True
    )
    from_user = db.relationship(
        "TelegramUser", back_populates="messages", foreign_keys=[from_user_id]
    )

    # Date the message was sent
    date = db.Column("message_date", db.DateTime, index=True, default=datetime.utcnow)

    # Optional. For forwarded messages, sender of the original message
    forward_from_id = db.Column(BigIntegerType, db.ForeignKey("telegram_user.id"))
    forward_from = db.relationship("TelegramUser", foreign_keys=[forward_from_id])

    # Optional. For messages forwarded from channels, information about the original channel
    forward_from_chat_id = db.Column(BigIntegerType)
    # Optional. For messages forwarded from channels, identifier of the
    # original message in the channel
    forward_from_message_id = db.Column(BigIntegerType)
    forward_signature = db.Column(db.String(200))
    forward_sender_name = db.Column(db.String(200))
    forward_date = db.Column(db.DateTime)

    # Reply
    reply_to_message_id = db.Column(BigIntegerType)
    reply_to_chat_id = db.Column(BigIntegerType)
    reply_to_message = db.relationship(
        "TelegramMessage",
        primaryjoin=and_(
            bot_id == foreign(bot_id),
            chat_id == foreign(reply_to_chat_id),
            message_id == foreign(reply_to_message_id),
        ),
        back_populates="replies",
        foreign_keys=[bot_id, reply_to_chat_id, reply_to_message_id],
        remote_side=[bot_id, chat_id, message_id],
    )
    replies = db.relationship(
        "TelegramMessage",
        primaryjoin=and_(
            bot_id == foreign(bot_id),
            chat_id == foreign(reply_to_chat_id),
            message_id == foreign(reply_to_message_id),
        ),
        back_populates="reply_to_message",
        foreign_keys=[bot_id, chat_id, message_id],
    )

    via_bot_id = db.Column(BigIntegerType)
    edit_date = db.Column(db.DateTime)
    media_group_id = db.Column(db.String(80))
    author_signature = db.Column(db.String(200))
    text = db.Column(db.Text)
    entities = db.relationship(
        "TelegramMessageEntity", back_populates="message", cascade="all,delete-orphan"
    )

    # Class constants
    RE_ESCAPE_COMMON = r"_*[]()~`>#+-=|{}.!"
    """A regular expression for escaping markup characters when converting
    a message text to markdown v2 representation. Used for escaping the
    contents of all entity types except "pre", "code", and URL parts of links
    """
    RE_ESCAPE_CODE = r"\`"
    """A regular expression for escaping special characters in "code"
    and "pre" entities
    """
    RE_ESCAPE_URL = r"\)"
    """A regular expression for escaping special characters in URL parts
    of the entities representing any kind of links
    """

    def __repr__(self):
        return f"<Message(chat_id={self.chat_id} message_id={self.message_id})>"

    @staticmethod
    def from_dict(d: dict, bot_id: int) -> "TelegramMessage":  # pylint: disable=invalid-name
        """Constructs an object from a dict

        :param d: A dictionary to construct the object from. Should contain a valid primary key
            and an arbitrary number of model attributes. If an object with the given primary key
            is found in the persistent storage, it will first be loaded, otherwise a new object
            with default attribute values will be created. After that, any attribute values present
            in `d` will update corresponding object fields.
        :param bot_id: ID of a bot that processed the message
        :return: An up-to-date data object.
        """
        msg = TelegramMessage.query.filter_by(
            bot_id=bot_id, chat_id=d["chat"]["id"], message_id=d["message_id"]
        ).first() or TelegramMessage(
            bot_id=bot_id, chat_id=d["chat"]["id"], message_id=d["message_id"]
        )
        chat = d.get("chat", None)
        if chat:
            msg.chat = BaseModel.TelegramChat.from_dict(chat)
        from_user = d.get("from", None)
        if from_user:
            msg.from_user = BaseModel.TelegramUser.from_dict(from_user)

        # Telegram provides date the message was sent in Unix time.
        # Convert it do datetime object.
        dt = d.get("date", None)  # pylint: disable=invalid-name
        msg.date = datetime.fromtimestamp(dt) if dt else None

        forward_from = d.get("forward_from", None)
        if forward_from:
            msg.forward_from = BaseModel.TelegramUser.from_dict(forward_from)
        msg.forward_from_chat_id = d.get("forward_from_chat_id", None)
        msg.forward_from_message_id = d.get("forward_from_message_id", None)
        msg.forward_signature = d.get("forward_signature", None)
        msg.forward_sender_name = d.get("forward_sender_name", None)
        dt = d.get("forward_date", None)  # pylint: disable=invalid-name
        msg.forward_date = datetime.fromtimestamp(dt) if dt else None

        reply_to = d.get("reply_to_message", None)
        if reply_to:
            reply_to_message = TelegramMessage.from_dict(reply_to, bot_id)
            msg.reply_to_message = reply_to_message

        msg.via_bot_id = d.get("via_bot_id", None)
        dt = d.get("edit_date", None)  # pylint: disable=invalid-name
        msg.edit_date = datetime.fromtimestamp(dt) if dt else None
        msg.media_group_id = d.get("media_group_id", None)
        msg.author_signature = d.get("author_signature", None)
        msg.text = d.get("text", None)
        BaseModel.TelegramMessageEntity.query.filter_by(
            bot_id=msg.bot_id, chat_id=msg.chat_id, message_id=msg.message_id
        ).delete()
        msg.entities = [
            BaseModel.TelegramMessageEntity.from_dict(e, msg.bot_id, msg.chat_id, msg.message_id)
            for e in d.get("entities", [])
        ]
        return msg

    @property
    def bot_commands(self) -> "OrderedDict[str, List[str]]":
        """Extracts a list of bot commands from the message

        Any text after a command entity is treated as command parameters,
        separated by spaces. Returns `dict` where keys are command names
        and values are command parameters.
        """
        result = OrderedDict()
        # Note: since Python 3.9 `typing.OrderedDict` is deprecated in favor
        # of `collections.OrderedDict`, which is now supports `[]`.
        # https://docs.python.org/3/library/typing.html#typing.OrderedDict
        if isinstance(self.text, str):
            for ent in self.entities:  # type: ignore # pylint: disable=not-an-iterable
                if ent.entity_type == "bot_command":
                    cmd = self.text[ent.offset : ent.length]  # noqa: E203
                    params = self.text[ent.offset + ent.length :].strip().split(" ")  # noqa: E203
                    if cmd not in result:
                        result[cmd] = params
        return result

    def get_markdown_v2_text(self, offset: int = 0) -> Optional[str]:
        """Parses the message and formats its text as markdown v2"""

        # Don't deal with messages with no text.
        # Also ensures that self.text is an "str" allowing for correct further type checking
        if not isinstance(self.text, str):
            return self.text

        message_text: str = self.text

        # Type casting to evade further type checking problems
        entities: List["TelegramMessageEntity"] = self.entities  # type: ignore
        processed_entities: List["TelegramMessageEntity"] = []
        if entities:
            sorted_entities: List["TelegramMessageEntity"] = sorted(
                entities, key=attrgetter("length"), reverse=True
            )
            sorted_entities = sorted(sorted_entities, key=attrgetter("offset"))
        else:
            sorted_entities = []

        def process_entity(entity: Optional["TelegramMessageEntity"]) -> str:
            """A closure that will parse a single message entity

            Parses a single entity of message and returns markdown representation of
            the corresponding text. If the given entity has nested entities, those
            will be recursively parsed as well.
            """
            if entity is None:
                entity_offset = offset
                entity_length = len(message_text) - entity_offset
                re_escape = self.__class__.RE_ESCAPE_COMMON
            else:
                entity_offset = entity.offset
                entity_length = entity.length
                if entity.entity_type in (
                    "code",
                    "pre",
                ):
                    re_escape = self.__class__.RE_ESCAPE_CODE
                elif entity.entity_type == "text_link":
                    re_escape = self.__class__.RE_ESCAPE_URL
                else:
                    re_escape = self.__class__.RE_ESCAPE_COMMON

            text_chunks: List[str] = []
            current_offset: int = entity_offset
            nested_entities: List["TelegramMessageEntity"] = []

            if entity is not None and entity not in processed_entities:
                processed_entities.append(entity)

            if entity is None or entity.entity_type not in ("pre", "code"):
                for nested_entity in sorted_entities:  # type: TelegramMessageEntity
                    if (
                        nested_entity.offset >= entity_offset
                        and nested_entity.offset + nested_entity.length
                        <= entity_offset + entity_length
                        and nested_entity != entity
                        and nested_entity not in processed_entities
                    ):
                        nested_entities.append(nested_entity)

            if nested_entities:
                for nested_entity in nested_entities:
                    # Process plain text preceding an entity, if any
                    if current_offset < nested_entity.offset:
                        text_chunks.append(
                            re.sub(
                                f"([{re.escape(re_escape)}])",
                                r"\\\1",
                                message_text[current_offset : nested_entity.offset],  # noqa: E203
                            )
                        )
                        current_offset = nested_entity.offset
                    # Precess an entity
                    if nested_entity not in processed_entities:
                        text_chunks.append(process_entity(nested_entity))
                    current_offset = nested_entity.offset + nested_entity.length

            # Append trailing chunk of text after the last processed entity
            if current_offset < entity_offset + entity_length:
                text_chunks.append(
                    re.sub(
                        f"([{re.escape(self.__class__.RE_ESCAPE_COMMON)}])",
                        r"\\\1",
                        message_text[current_offset : entity_offset + entity_length],  # noqa: E203
                    )
                )

            text = "".join(text_chunks)

            if entity is None:
                # A top-level call - return the text as-is. It should already
                # include all the nested entities parsed and formatted.
                pass
            elif entity.entity_type == "bold":
                text = f"*{text}*"
            elif entity.entity_type == "italic":
                text = f"_{text}_"
            elif entity.entity_type == "underline":
                text = f"__{text}__"
            elif entity.entity_type == "strikethrough":
                text = f"~{text}~"
            elif entity.entity_type == "pre":
                lang = f"{entity.language}\n" if entity.language else ""
                prefix = "\n" if text.startswith("\\") and not lang else ""
                text = f"```{prefix}{lang}{text}```"
            elif entity.entity_type == "code":
                text = f"`{text}`"
            elif entity.entity_type == "url":
                assert entity.url is not None
                url = re.sub(f"([{re.escape(self.__class__.RE_ESCAPE_URL)}])", r"\\\1", entity.url)
                text = f"[{text}]({url})"
            elif entity.entity_type == "text_link":
                assert entity.url is not None
                url = re.sub(f"([{re.escape(self.__class__.RE_ESCAPE_URL)}])", r"\\\1", entity.url)
                text = f"[{text}]({url})"
            elif entity.entity_type == "text_mention" and entity.tm_user:
                text = f"[{text}](tg://user?id={entity.tm_user_id})"
            return text

        return process_entity(None)


BaseModel.TelegramMessage = TelegramMessage
