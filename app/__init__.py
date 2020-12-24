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
from logging.handlers import SMTPHandler
from typing import Type, Union

import rq
from flask import Flask
from flask import logging as flask_logging
from redis import Redis

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

    gunicorn_error_logger = logging.getLogger("gunicorn.error")
    app.logger.handlers.extend(gunicorn_error_logger.handlers)
    app.logger.setLevel(app_log_level)

    if (
        app_log_level == logging.DEBUG
        and not app.testing
        and os.environ.get("WERKZEUG_RUN_MAIN", "false") == "false"
    ):
        app.logger.info("Debug logging enabled")

    # Instantiate the bot dispatcher object
    if not app.testing and not app.config["BOT_TOKEN"] and not app.config["BOT_USER_ID"]:
        raise ENoBotConfigured("No BOT_TOKEN or BOT_USER_ID found in configuration")
    app.bot_dispatcher = BotDispatcher.get(app.config["BOT_TOKEN"])

    # Attach Flask extensions
    db.init_app(app)
    migrate.init_app(app, db)

    # Hook up blueprints
    # ToDo: add flask blueprints

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

    return app


def enable_stdout_logging(app: Flask, log_level: Union[str, int] = None) -> None:
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


def register_shell_context(app: BotApp) -> None:
    """Register app shell context"""

    @app.shell_context_processor
    def make_shell_context():  # pylint: disable=unused-variable
        return {"app": app, "db": db, "bot": app.bot_dispatcher}
