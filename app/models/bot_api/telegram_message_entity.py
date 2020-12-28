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
"""Telegram message entity data model"""
from typing import TYPE_CHECKING

from common.db import BaseModel, BigIntegerType, PersistableMixin, db

if TYPE_CHECKING:
    from .telegram_message import TelegramMessage  # noqa: F401
    from .telegram_user import TelegramUser  # noqa: F401


class TelegramMessageEntity(BaseModel, PersistableMixin):
    """MessageEntity object model from Telegram Bot API

    https://core.telegram.org/bots/api#messageentity
    This object represents one special entity in a text message.
    For example, hashtags, usernames, URLs, etc.
    """

    __tablename__ = "telegram_message_entity"
    id = db.Column(BigIntegerType, primary_key=True, autoincrement=True)
    bot_id = db.Column(BigIntegerType, index=True, nullable=False)
    chat_id = db.Column(BigIntegerType, index=True, nullable=False)
    message_id = db.Column(BigIntegerType, index=True, nullable=False)
    message = db.relationship(
        "TelegramMessage",
        foreign_keys=[bot_id, chat_id, message_id],
        back_populates="entities",
    )
    entity_type = db.Column(db.String(40), autoincrement=False)
    offset = db.Column(db.Integer, nullable=False)
    length = db.Column(db.Integer, nullable=False)
    url = db.Column(db.Text)
    tm_user_id = db.Column(BigIntegerType, db.ForeignKey("telegram_user.id"), nullable=True)
    tm_user = db.relationship("TelegramUser", back_populates="text_mentions")
    language = db.Column(db.String(40))

    __table_args__ = (
        db.ForeignKeyConstraint(
            ["bot_id", "chat_id", "message_id"],
            [
                BaseModel.TelegramMessage.bot_id,
                BaseModel.TelegramMessage.chat_id,
                BaseModel.TelegramMessage.message_id,
            ],
            ondelete="cascade",
        ),
    )

    @staticmethod
    def from_dict(  # pylint: disable=invalid-name
        d: dict, bot_id: int, chat_id: int, message_id: int
    ) -> "TelegramMessageEntity":
        """Constructs an object from a dict

        :param d: A dictionary to construct the object from. Should contain a valid primary key
            and an arbitrary number of model attributes. If an object with the given primary key
            is found in the persistent storage, it will first be loaded, otherwise a new object
            with default attribute values will be created. After that, any attribute values present
            in `d` will update corresponding object fields.
        :param bot_id: ID of a bot that processed the message
        :param chat_id: ID of a chat the message was posted to
        :param message_id: ID of a message the entity belongs to
        :return: An up-to-date data object.
        """
        ent = TelegramMessageEntity(bot_id=bot_id, chat_id=chat_id, message_id=message_id)
        ent.entity_type = d["type"]
        ent.offset = d["offset"]
        ent.length = d["length"]
        ent.url = d.get("url", None)
        u = d.get("user", None)  # pylint: disable=invalid-name
        if u:
            ent.tm_user = BaseModel.TelegramUser.from_dict(u)
        ent.language = d.get("language", None)

        return ent


BaseModel.TelegramMessageEntity = TelegramMessageEntity
