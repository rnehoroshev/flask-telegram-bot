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
"""Custom Flask application"""
from typing import Optional

from flask import Flask

from telegram_bot import BotDispatcher


class BotApp(Flask):
    """Flask application class extended with application-specific attributes"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Application-specific fields and methods
        self.bot_dispatcher = None  # type: Optional[BotDispatcher]
