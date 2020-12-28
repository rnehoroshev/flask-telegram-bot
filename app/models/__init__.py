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
"""Flask application data model"""
from typing import TYPE_CHECKING, Type

if TYPE_CHECKING:
    from flask_sqlalchemy.model import Model  # pylint: disable=ungrouped-imports

    class AppModel(Model):  # pylint: disable=too-few-public-methods
        """Extended application model holding all the declared model classes as attributes

        Makes static type analysers happy.
        """

        TelegramBot: Type  # Trying to assign a concrete type results in circular imports
        TelegramUser: Type
        TelegramChat: Type
        TelegramChatType: Type
        BotAdmin: Type
        BotAdminChat: Type
        BotCommand: Type
        BotForwardChat: Type
        BotReplyText: Type
        BotSubscriber: Type
        TelegramMessage: Type
        TelegramMessageEntity: Type
