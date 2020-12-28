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
"""Telegram bot data model"""
from typing import TYPE_CHECKING

from sqlalchemy import func
from sqlalchemy.sql.expression import true

from common.db import BaseModel, BigIntegerType, PersistableMixin, db
from telegram_bot import BotDispatcher

if TYPE_CHECKING:
    from .bot_admin import BotAdmin  # noqa: F401
    from .bot_admin_chat import BotAdminChat  # noqa: F401
    from .bot_command import BotCommand  # noqa: F401
    from .bot_forward_chat import BotForwardChat  # noqa: F401
    from .bot_reply_text import BotReplyText  # noqa: F401
    from .bot_subscriber import BotSubscriber  # noqa: F401
    from .telegram_message import TelegramMessage  # noqa: F401
    from .telegram_user import TelegramUser  # noqa: F401


class TelegramBot(BaseModel, PersistableMixin):
    """Telegram bot"""

    __tablename__ = "telegram_bot"
    user_id = db.Column(
        BigIntegerType, db.ForeignKey("telegram_user.id"), primary_key=True, autoincrement=False
    )
    token = db.Column(db.String(60))
    user = db.relationship("TelegramUser", foreign_keys=[user_id])
    commands = db.relationship(
        "BotCommand", back_populates="bot", cascade="all,delete-orphan", lazy="dynamic"
    )

    admins = db.relationship(
        "BotAdmin", back_populates="bot", cascade="all,delete-orphan", lazy="dynamic"
    )
    subscribers = db.relationship("BotSubscriber", back_populates="bot", lazy="dynamic")

    chats_admin = db.relationship(
        "BotAdminChat", back_populates="bot", cascade="all,delete-orphan", lazy="dynamic"
    )
    chats_forward = db.relationship(
        "BotForwardChat", back_populates="bot", cascade="all,delete-orphan", lazy="dynamic"
    )

    reply_texts = db.relationship(
        "BotReplyText", back_populates="bot", cascade="all,delete-orphan", lazy="dynamic"
    )

    messages = db.relationship("TelegramMessage", back_populates="bot", lazy="dynamic")

    @staticmethod
    def register_bot(token: str) -> "TelegramBot":
        """Registers or updates the bot configuration in a database"""
        bot_dispatcher = BotDispatcher(token)
        bot = TelegramBot.query.filter_by(user_id=bot_dispatcher.user_id).first() or TelegramBot(
            user_id=bot_dispatcher.user_id, user=BaseModel.TelegramUser(id=bot_dispatcher.user_id)
        )
        if token != bot.token:
            bot.token = token
        bot = db.session.merge(bot)

        return bot

    @property
    def sub_count(self) -> int:
        """Return the number of active subscribers"""
        if TYPE_CHECKING:
            subscriber: BotSubscriber  # pylint: disable=used-before-assignment
        subscriber = BaseModel.BotSubscriber  # type: ignore
        sub_count = (
            db.session.query(func.count(subscriber.user_id))  # pylint: disable=no-member
            .filter(subscriber.active == true() and subscriber.bot_id == self.user_id)
            .first()[0]
        )
        return sub_count

    def __repr__(self) -> str:
        """Default string representation"""
        return f"<TelegramBot({self.user_id})>"


BaseModel.TelegramBot = TelegramBot
