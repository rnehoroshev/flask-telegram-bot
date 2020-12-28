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
"""Bot subscriber data model"""
from typing import TYPE_CHECKING

from sqlalchemy.sql import expression

from common.db import BaseModel, BigIntegerType, PersistableMixin, db

if TYPE_CHECKING:
    from .telegram_bot import TelegramBot  # noqa: F401
    from .telegram_user import TelegramUser  # noqa: F401


class BotSubscriber(BaseModel, PersistableMixin):  # pylint: disable=too-few-public-methods
    """List of bots a user is subscribed to"""

    __tablename__ = "bot_subscriber"
    bot_id = db.Column(
        BigIntegerType,
        db.ForeignKey("telegram_bot.user_id"),
        primary_key=True,
        index=True,
        autoincrement=False,
    )
    bot = db.relationship("TelegramBot", back_populates="subscribers", uselist=False)

    user_id = db.Column(
        BigIntegerType,
        db.ForeignKey("telegram_user.id"),
        primary_key=True,
        index=True,
        autoincrement=False,
    )
    user = db.relationship("TelegramUser", back_populates="bots_subscribed", uselist=False)

    active = db.Column(db.Boolean, server_default=expression.true(), nullable=False)


BaseModel.BotSubscriber = BotSubscriber
