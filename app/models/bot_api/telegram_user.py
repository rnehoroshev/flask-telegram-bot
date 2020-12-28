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
"""Telegram user data model"""
from typing import TYPE_CHECKING

from common.db import BaseModel, BigIntegerType, PersistableMixin, db

if TYPE_CHECKING:
    from .bot_admin import BotAdmin  # noqa: F401
    from .bot_subscriber import BotSubscriber  # noqa: F401
    from .telegram_message import TelegramMessage  # noqa: F401
    from .telegram_message_entity import TelegramMessageEntity  # noqa: F401


class TelegramUser(BaseModel, PersistableMixin):
    """User object model from Telegram Bot API

    https://core.telegram.org/bots/api#user
    """

    __tablename__ = "telegram_user"
    id = db.Column(BigIntegerType, primary_key=True, autoincrement=False)
    is_bot = db.Column(db.Boolean)
    first_name = db.Column(db.String(200))
    last_name = db.Column(db.String(200))
    username = db.Column(db.String(200), index=True)
    language_code = db.Column(db.String(20))
    can_join_groups = db.Column(db.Boolean)
    can_read_all_group_messages = db.Column(db.Boolean)
    supports_inline_queries = db.Column(db.Boolean)
    bots_admin = db.relationship("BotAdmin", back_populates="user", cascade="all,delete-orphan")
    bots_subscribed = db.relationship(
        "BotSubscriber", back_populates="user", cascade="all,delete-orphan"
    )
    messages = db.relationship(
        "TelegramMessage",
        back_populates="from_user",
        lazy="dynamic",
        foreign_keys=[BaseModel.TelegramMessage.from_user_id],
    )
    text_mentions = db.relationship("TelegramMessageEntity", back_populates="tm_user")

    @staticmethod
    def from_dict(d: dict) -> "TelegramUser":  # pylint: disable=invalid-name
        """Constructs an object from a dict

        :param d: A dictionary to construct the object from. Should contain a valid primary key
            and an arbitrary number of model attributes. If an object with the given primary key
            is found in the persistent storage, it will first be loaded, otherwise a new object
            with default attribute values will be created. After that, any attribute values present
            in `d` will update corresponding object fields.
        :return: An up-to-date data object.
        """
        user = TelegramUser.query.filter_by(id=d["id"]).first() or TelegramUser(id=d["id"])
        user.is_bot = d.get("is_bot", None)
        user.first_name = d.get("first_name", None)
        user.last_name = d.get("last_name", None)
        user.username = d.get("username", None)
        user.language_code = d.get("language_code", None)
        user.can_join_groups = d.get("can_join_groups", None)
        user.can_read_all_group_messages = d.get("can_read_all_group_messages", None)
        user.supports_inline_queries = d.get("supports_inline_queries", None)

        return user

    def is_admin(self, bot_id: int) -> bool:
        """`True` if user is an admin for the given bot"""
        adm = BaseModel.BotAdmin.query.filter_by(bot_id=bot_id, user_id=self.id).first()
        return False if not adm else adm.active

    def is_subscriber(self, bot_id: int) -> bool:
        """`True` if user is a subscriber of the given bot"""
        sub = BaseModel.BotSubscriber.query.filter_by(bot_id=bot_id, user_id=self.id).first()
        return False if not sub else sub.active

    def subscribe(self, bot_id: int) -> "BotSubscriber":
        """Subscribes user to the given bot"""
        sub = BaseModel.BotSubscriber.query.filter_by(bot_id=bot_id, user_id=self.id).first()
        if not sub:
            sub = db.session.merge(
                BaseModel.BotSubscriber(bot_id=bot_id, user_id=self.id, active=True)
            )
        elif not sub.active:
            sub.active = True

        return sub

    def unsubscribe(self, bot_id: int) -> None:
        """Unsubscribes user from the given bot"""
        sub = BaseModel.BotSubscriber.query.filter_by(bot_id=bot_id, user_id=self.id).first()
        if sub and sub.active:
            sub.active = False

    def set_admin(self, bot_id: int) -> "BotAdmin":
        """Makes user an admin for the given bot"""
        return db.session.merge(BaseModel.BotAdmin(bot_id=bot_id, user_id=self.id, active=True))

    def revoke_admin(self, bot_id: int) -> None:
        """Revokes an admin status from the user"""
        db.session.merge(BaseModel.BotAdmin(bot_id=bot_id, user_id=self.id, active=False))


BaseModel.TelegramUser = TelegramUser
