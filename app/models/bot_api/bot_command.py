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
"""Telegram bot command data model"""
from typing import TYPE_CHECKING

from common.db import BaseModel, BigIntegerType, PersistableMixin, db

if TYPE_CHECKING:
    from .telegram_bot import TelegramBot  # noqa: F401


class BotCommand(BaseModel, PersistableMixin):
    """BotCommand object model from Telegram Bot API

    https://core.telegram.org/bots/api#botcommand
    This object represents a bot command.
    """

    __tablename__ = "bot_command"
    bot_id = db.Column(
        BigIntegerType,
        db.ForeignKey("telegram_bot.user_id"),
        primary_key=True,
        index=True,
        autoincrement=False,
    )
    command = db.Column(db.String(50), primary_key=True, index=True, autoincrement=False)
    description = db.Column(db.String(500))
    bot = db.relationship("TelegramBot", back_populates="commands")

    @staticmethod
    def from_dict(d: dict, bot_id: int) -> "BotCommand":  # pylint: disable=invalid-name
        """Constructs an object from a dict

        :param d: A dictionary to construct the object from. Should contain a valid primary key
            and an arbitrary number of model attributes. If an object with the given primary key
            is found in the persistent storage, it will first be loaded, otherwise a new object
            with default attribute values will be created. After that, any attribute values present
            in `d` will update corresponding object fields.
        :param bot_id: ID of a bot that owns the command
        :return: An up-to-date data object.
        """
        cmd = BotCommand.query.filter_by(
            bot_id=bot_id, command=d["command"]
        ).first() or BotCommand(bot_id=bot_id, command=d["command"])
        cmd.description = d.get("description", None)

        return cmd

    def to_dict(self) -> dict:
        """Returns a dict representation of an object"""
        return {"command": self.command, "description": self.description}


BaseModel.BotCommand = BotCommand
