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
"""Flask application factory"""
import logging
import os
import sys
from logging.handlers import RotatingFileHandler, SMTPHandler
from pathlib import Path
from typing import Optional, Sequence, Type, Union

import rq
from flask import Flask
from flask import logging as flask_logging
from redis import Redis

from app.bot_handlers import register_handlers
from common import PathUtils
from common.db import db, migrate
from common.logging import RelativePathsFormatter
from config import DEFAULT_LOG_FORMAT, Config, basedir
from telegram_bot import BotDispatcher

from . import cli
from .bot_app import BotApp
from .exceptions import ENoBotConfigured


def create_app(config_class: Type = Config) -> BotApp:
    """Main application factory"""

    # Setup default Flask logger (before read config)
    flask_logging.default_handler.setFormatter(
        RelativePathsFormatter(DEFAULT_LOG_FORMAT, paths_relative_to=basedir)
    )

    # Create application instance and read config
    app = BotApp(__name__)
    app.config.from_object(config_class)

    # Configure advanced logging (after read config)
    app_log_level = logging.getLevelName(app.config.get("LOG_LEVEL", "INFO"))
    flask_logging.default_handler.setLevel(app_log_level)

    if not app.debug and not app.testing:
        if app.config["LOG_TO_STDOUT"]:
            enable_stdout_logging(app)

    enable_email_logging(app)

    # Enable file logging if configured
    log_dir = app.config["LOG_FILE_DIR"]
    if log_dir and PathUtils.is_path_exists_or_creatable(log_dir):
        enable_file_logging(
            app, log_dir, log_level=logging.getLevelName(app.config.get("LOG_LEVEL", None))
        )

    gunicorn_error_logger = logging.getLogger("gunicorn.error")
    app.logger.handlers.extend(gunicorn_error_logger.handlers)
    app.logger.setLevel(app_log_level)

    if (
        app_log_level == logging.DEBUG
        and not app.testing
        and os.environ.get("WERKZEUG_RUN_MAIN", "false") == "false"
    ):
        app.logger.info("Debug logging enabled")

    # Prepare updates dump dir if required
    dump_updates = bool(app.config.get("DUMP_UPDATES", False))
    updates_dump_dir = app.config.get("UPDATES_DUMP_DIR", None)
    if dump_updates:
        if PathUtils.is_path_exists_or_creatable(updates_dump_dir):
            Path(updates_dump_dir).mkdir(parents=True, exist_ok=True)
        else:
            app.logger.warn(
                f"Unable to create path {updates_dump_dir}. Update dumps will not be saved"
            )
            dump_updates = False
    app.config["DUMP_UPDATES"] = dump_updates

    # Instantiate the bot dispatcher object
    if not app.testing and not app.config["BOT_TOKEN"] and not app.config["BOT_USER_ID"]:
        raise ENoBotConfigured("No BOT_TOKEN or BOT_USER_ID found in configuration")
    app.bot_dispatcher = BotDispatcher.get(app.config["BOT_TOKEN"])

    # Attach Flask extensions
    db.init_app(app)
    migrate.init_app(app, db)

    # Hook up blueprints
    from app.bot import TelegramBotBlueprint  # pylint: disable=import-outside-toplevel
    from app.bot import __name__ as bot_package_name  # pylint: disable=import-outside-toplevel

    bot_blueprint = TelegramBotBlueprint(
        app.bot_dispatcher,
        f"bot{app.bot_dispatcher.user_id}",
        bot_package_name,
        url_prefix=f"/bot{app.bot_dispatcher.token}",
    )
    app.register_blueprint(bot_blueprint)

    # Setup redis connection and task queue
    app.redis = Redis.from_url(app.config["REDIS_URL"])
    app.task_queue = rq.Queue(app.config["RQ_NAME"], connection=app.redis)

    # Register app shell context
    register_shell_context(app)

    # Register CLI commands
    cli.register(app)

    # Application initialized successfully
    if not app.testing:
        if os.environ.get("WERKZEUG_RUN_MAIN", "false") == "false":
            app.logger.info(f"{app.config['BOT_NAME']} started in '{basedir}'")
        else:
            app.logger.info(f"{app.config['BOT_NAME']} restarted in '{basedir}'")

    register_bot_handlers(app)

    return app


def enable_stdout_logging(app: Flask, log_level: Optional[Union[str, int]] = None) -> None:
    """Enables logging to stdout with specified log level"""
    stream_handler = logging.StreamHandler(stream=sys.stdout)
    stream_handler.setLevel(
        log_level or logging.getLevelName(app.config["LOG_LEVEL"]) or logging.INFO
    )
    stream_handler.setFormatter(
        RelativePathsFormatter(DEFAULT_LOG_FORMAT, paths_relative_to=basedir)
    )
    app.logger.addHandler(stream_handler)


def enable_email_logging(app: Flask) -> None:
    """Enable sending errors to admins by email"""
    if app.config["MAIL_SERVER"]:
        auth = None
        if app.config["MAIL_USERNAME"] or app.config["MAIL_PASSWORD"]:
            auth = (app.config["MAIL_USERNAME"], app.config["MAIL_PASSWORD"])
        secure = None
        if app.config["MAIL_USE_TLS"]:
            secure = ()
        mail_handler = SMTPHandler(
            mailhost=(app.config["MAIL_SERVER"], app.config["MAIL_PORT"]),
            fromaddr="".join(
                (app.config["MAIL_ERROR_REPORTS_FROM_ADDR"], app.config["MAIL_SERVER"])
            ),
            toaddrs=app.config["ADMINS"],
            subject=f"An unexpected error occurred in {app.config['BOT_NAME']} application",
            credentials=auth,
            secure=secure,  # type: ignore
        )
        mail_handler.setLevel(logging.ERROR)
        app.logger.addHandler(mail_handler)


def enable_file_logging(
    app: Flask, log_dir: str, log_level: Optional[Union[int, str]] = None
) -> None:
    """Enables logging to file(s) with specified log level"""
    if not os.path.exists(log_dir):
        Path(log_dir).mkdir(parents=True, exist_ok=True)
    file_handler = RotatingFileHandler(
        os.path.join(log_dir, "bot.log"), maxBytes=10485760, backupCount=10
    )
    file_handler.setFormatter(
        RelativePathsFormatter(DEFAULT_LOG_FORMAT, paths_relative_to=basedir)
    )
    file_handler.setLevel(
        log_level or logging.getLevelName(app.config["LOG_LEVEL"]) or logging.INFO
    )
    app.logger.addHandler(file_handler)


def register_bot_handlers(app: BotApp) -> None:
    """Register configured bot update handlers within the app's bot dispatcher"""
    try:
        if isinstance(app.config["BOT_HANDLERS"], str):
            bot_update_handlers: Sequence[str] = app.config["BOT_HANDLERS"].split(",")
            bot_update_handlers = register_handlers(app.bot_dispatcher, bot_update_handlers)
        else:
            bot_update_handlers = []

        if not bot_update_handlers:
            app.logger.warn("No valid bot modules found")
        else:
            app.logger.info(
                "The following bot modules registered: %s", ",".join(bot_update_handlers)
            )
    except Exception as exc:
        app.logger.exception(
            f"An exception {type(exc).__name__} occurred while registering bot handler modules"
        )
        raise exc


def register_shell_context(app: BotApp) -> None:
    """Register app shell context"""

    # pylint: disable=import-outside-toplevel
    from app.models.bot_api import (
        BotAdmin,
        BotAdminChat,
        BotCommand,
        BotForwardChat,
        BotReplyText,
        BotSubscriber,
        TelegramBot,
        TelegramChat,
        TelegramChatType,
        TelegramMessage,
        TelegramMessageEntity,
        TelegramUser,
    )

    @app.shell_context_processor
    def make_shell_context():  # pylint: disable=unused-variable
        return {
            "app": app,
            "db": db,
            "bot": app.bot_dispatcher,
            "TelegramBot": TelegramBot,
            "TelegramUser": TelegramUser,
            "TelegramChat": TelegramChat,
            "TelegramChatType": TelegramChatType,
            "BotAdmin": BotAdmin,
            "BotAdminChat": BotAdminChat,
            "BotCommand": BotCommand,
            "BotForwardChat": BotForwardChat,
            "BotReplyText": BotReplyText,
            "BotSubscriber": BotSubscriber,
            "TelegramMessage": TelegramMessage,
            "TelegramMessageEntity": TelegramMessageEntity,
        }
