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
"""Bot reply text template data model"""
from typing import TYPE_CHECKING

from common.db import BaseModel, BigIntegerType, PersistableMixin, db

if TYPE_CHECKING:
    from .telegram_bot import TelegramBot  # noqa: F401


class BotReplyText(BaseModel, PersistableMixin):
    """Bot reply text template"""

    __tablename__ = "bot_reply_text"
    bot_id = db.Column(
        BigIntegerType,
        db.ForeignKey("telegram_bot.user_id"),
        primary_key=True,
        index=True,
        autoincrement=False,
    )
    code = db.Column(db.String(40), primary_key=True, index=True, autoincrement=False)
    text = db.Column(db.String(500))
    bot = db.relationship("TelegramBot", back_populates="reply_texts")

    @staticmethod
    def set_text(bot_id, code, text):
        """Set or update a specified reply text template"""
        db.session.merge(BotReplyText(bot_id=bot_id, code=code.lower().strip(), text=text))


BaseModel.BotReplyText = BotReplyText
