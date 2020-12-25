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
"""Default configuration class for Flask application instance"""
import os

from dotenv import load_dotenv

from common import email_list

basedir = os.path.abspath(os.path.dirname(__file__))

# Load environment from .env
dotenv_path = os.path.join(basedir, ".env")
load_dotenv(dotenv_path)

DEFAULT_LOG_FORMAT = "%(asctime)-15s [%(levelname)-8s] %(message)s (%(relpath)s:%(lineno)d)"


class Config:  # pylint: disable=too-few-public-methods
    """Default flask application config"""

    FLASK_ENV = os.environ.get("FLASK_ENV")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL") or "sqlite:///" + os.path.join(
        basedir, "bot.db"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    LOG_LEVEL = os.environ.get("BOT_LOG_LEVEL")
    LOG_TO_STDOUT = os.environ.get("BOT_LOG_TO_STDOUT") == "1"
    LOG_FILE_DIR = os.environ.get("BOT_LOG_FILE_DIR")

    MAIL_SERVER = os.environ.get("MAIL_SERVER")
    MAIL_PORT = int(os.environ.get("MAIL_PORT") or 25)
    MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS") is not None
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")
    MAIL_ERROR_REPORTS_FROM_ADDR = (
        os.environ.get("MAIL_ERROR_REPORTS_FROM_ADDR") or "no-reply@localhost"
    )

    ADMINS = [
        f"{name} <{email}>" if name else email
        for name, email in email_list(
            os.environ.get("BOT_ADMIN_EMAILS") or "admin <admin@localhost>"
        )
    ]

    # Telegram bot token
    BOT_TOKEN = os.environ.get("BOT_TOKEN")

    # Telegram user_id for the bot account.
    # Either BOT_TOKEN or BOT_USER_ID must be set.
    BOT_USER_ID = os.environ.get("BOT_USER_ID")

    # Bot name (for referring to in logs)
    BOT_NAME = os.environ.get("BOT_NAME") or "Telegram bot"

    # RQ config
    REDIS_URL = os.environ.get("BOT_REDIS_URL") or "redis://"
    RQ_NAME = os.environ.get("BOT_RQ_NAME") or "bot-tasks"
