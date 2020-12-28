#!/usr/bin/env python
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
"""Telegram chat data model"""
from typing import TYPE_CHECKING, Optional

from app.exceptions import EInappropriateChatType, EInvalidChatType
from common.db import BaseModel, BigIntegerType, PersistableMixin, db

if TYPE_CHECKING:
    from .bot_admin_chat import BotAdminChat  # noqa: F401
    from .bot_forward_chat import BotForwardChat  # noqa: F401
    from .telegram_message import TelegramMessage  # noqa: F401


class TelegramChat(BaseModel, PersistableMixin):
    """Chat object model from Telegram Bot API

    https://core.telegram.org/bots/api#chat
    This object represents a chat.
    """

    __tablename__ = "telegram_chat"
    id = db.Column(BigIntegerType, primary_key=True, autoincrement=False)
    type_code = db.Column(db.CHAR(1), db.ForeignKey("chat_type.code"), index=True, nullable=False)
    type = db.relationship("TelegramChatType", back_populates="chats")
    title = db.Column(db.String(500))
    username = db.Column(db.String(500))
    first_name = db.Column(db.String(500))
    last_name = db.Column(db.String(500))
    photo_id = db.Column(BigIntegerType)
    description = db.Column(db.Text)
    invite_link = db.Column(db.Text)
    bots_forward_here = db.relationship(
        "BotForwardChat", back_populates="chat", cascade="all,delete-orphan", lazy="dynamic"
    )
    bots_listen_here = db.relationship(
        "BotAdminChat", back_populates="chat", cascade="all,delete-orphan", lazy="dynamic"
    )
    messages = db.relationship("TelegramMessage", back_populates="chat")

    @staticmethod
    def from_dict(d: dict) -> "TelegramChat":  # pylint: disable=invalid-name
        """Constructs an object from a dict

        :param d: A dictionary to construct the object from. Should contain a valid primary key
            and an arbitrary number of model attributes. If an object with the given primary key
            is found in the persistent storage, it will first be loaded, otherwise a new object
            with default attribute values will be created. After that, any attribute values present
            in `d` will update corresponding object fields.
        :return: An up-to-date data object.
        """
        chat = BaseModel.TelegramChat.query.filter_by(id=d["id"]).first() or TelegramChat(
            id=d["id"]
        )
        chat_type = d.get("type", None)
        if chat_type:
            chat.type = db.session.merge(BaseModel.TelegramChatType(chat_type))
            chat.type_code = chat.type.code
        chat.title = d.get("title", None)
        chat.username = d.get("username", None)
        chat.first_name = d.get("first_name", None)
        chat.last_name = d.get("last_name", None)
        chat.description = d.get("description", None)
        chat.invite_link = d.get("invite_link", None)

        return chat

    def is_admin_channel(self, bot_id: int) -> bool:
        """`True` if chat is an admin channel for the given bot"""
        return (
            self.type_code in ("g", "s")
            and BaseModel.BotAdminChat.query.filter_by(bot_id=bot_id, chat_id=self.id).first()
            is not None
        )

    def is_forward_channel(self, bot_id: int) -> bool:
        """`True` if chat is a forward channel for the given bot"""
        return (
            self.type_code in ("g", "s")
            and BaseModel.BotForwardChat.query.filter_by(bot_id=bot_id, chat_id=self.id).first()
            is not None
        )

    def set_admin_channel(self, bot_id: int):
        """Makes chat an admin channel for the given bot"""
        if self.type_code in ("g", "s"):
            db.session.merge(BaseModel.BotAdminChat(bot_id=bot_id, chat_id=self.id))
        else:
            raise EInappropriateChatType("Only group chats can be set as administrative")

    def set_forward_channel(self, bot_id: int):
        """Makes chat a forward channel for the given bot"""
        if self.type_code in ("g", "s"):
            db.session.merge(BaseModel.BotForwardChat(bot_id=bot_id, chat_id=self.id))
        else:
            raise EInappropriateChatType("Only group chats can be set as forward targets")

    def revoke_admin_channel(self, bot_id: int):
        """Revokes an admin channel status from the chat"""
        if self.type_code in ("g", "s"):
            BaseModel.BotAdminChat.query.filter_by(bot_id=bot_id, chat_id=self.id).delete()
        else:
            raise EInappropriateChatType("Only group chats can be set as administrative")

    def revoke_forward_channel(self, bot_id: int):
        """Revokes a forward channel status from the chat"""
        if self.type_code in ("g", "s"):
            BaseModel.BotForwardChat.query.filter_by(bot_id=bot_id, chat_id=self.id).delete()
        else:
            raise EInappropriateChatType("Only group chats can be set as forward targets")


class TelegramChatType(BaseModel, PersistableMixin):
    """Chat type"""

    __tablename__ = "chat_type"
    _type_to_code = {"private": "p", "group": "g", "supergroup": "s", "channel": "c"}
    code = db.Column(db.CHAR(1), primary_key=True, autoincrement=False)
    _name_field = db.Column("name", db.String(20))
    chats = db.relationship("TelegramChat", back_populates="type")

    @property
    def name(self) -> Optional[str]:
        """Return a human-readable name (description) of chat type

        This name is one of the supported by the Telegram Bot API values for chat types.
        It is used in JSON objects for chat descriptions. However, for the sake of optimization,
        we want to store a shorter single-char code in our DB. Hence the code/name conversion
        routines.
        """
        # Maybe use attribute change events instead of class properties?
        # https://docs.sqlalchemy.org/en/13/orm/session_events.html#attribute-change-events
        return self._name_field

    @name.setter
    def name(self, value: str) -> None:
        """Chat type name setter

        Updates code consistently with the name

        :param value: Telegram chat type name, as described in Telegram Bot API (attribute "type"
            of the "Chat" object: https://core.telegram.org/bots/api#chat)

        :raise KeyError: when given value is not one of the known possibilities
        """
        v = value.strip().lower()  # pylint: disable=invalid-name
        self.code = self._type_to_code[v]
        self._name_field = v

    def __init__(self, name, code: Optional[str] = None, **kwargs):
        if not name or not isinstance(name, str):
            raise EInvalidChatType("Unknown chat type", name)
        n = name.strip().lower()  # pylint: disable=invalid-name
        c = self._type_to_code[n]  # pylint: disable=invalid-name
        if code and code != c.strip().lower():
            raise EInvalidChatType("Inconsistent chat code", code, name)

        super().__init__(name=n, **kwargs)  # type: ignore
        # MyPy has several unsolved issues with super().__init__() and mixins:
        # https://github.com/python/mypy/issues/5887
        # https://github.com/python/mypy/issues/4001
        # Ignoring this line until a better solution is found

        self.code = c
        self.name = n

    def __repr__(self):
        """Default string representation"""
        return f'<TelegramChatType(code="{self.code}" name="{self.name}")>'


BaseModel.TelegramChatType = TelegramChatType
BaseModel.TelegramChat = TelegramChat
