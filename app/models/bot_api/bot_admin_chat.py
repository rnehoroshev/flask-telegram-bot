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
"""Bot admin chat data model"""
from typing import TYPE_CHECKING

from common.db import BaseModel, BigIntegerType, PersistableMixin, db

if TYPE_CHECKING:
    from .telegram_bot import TelegramBot  # noqa: F401
    from .telegram_chat import TelegramChat  # noqa: F401


class BotAdminChat(BaseModel, PersistableMixin):  # pylint: disable=too-few-public-methods
    """List of chats a bot will listen to commands in"""

    __tablename__ = "bot_admin_chat"

    bot_id = db.Column(
        BigIntegerType,
        db.ForeignKey("telegram_bot.user_id"),
        primary_key=True,
        index=True,
        autoincrement=False,
    )
    bot = db.relationship("TelegramBot", back_populates="chats_admin", uselist=False)

    chat_id = db.Column(
        BigIntegerType,
        db.ForeignKey("telegram_chat.id"),
        primary_key=True,
        index=True,
        autoincrement=False,
    )
    chat = db.relationship("TelegramChat", back_populates="bots_listen_here", uselist=False)


BaseModel.BotAdminChat = BotAdminChat
