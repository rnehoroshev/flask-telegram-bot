#!/usr/bin/env python
# pylint: disable=too-many-branches,too-many-statements,unsubscriptable-object
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
"""A sample and simple bot implementation"""
import re
from typing import List, Optional

from flask import current_app

from app import BotApp
from app.exceptions import EInappropriateChatType
from app.models.bot_api import (
    BotCommand,
    BotForwardChat,
    BotReplyText,
    TelegramBot,
    TelegramChat,
    TelegramMessage,
)
from telegram_bot import BotDispatcher


class UpdateHandler:
    """Incoming update handler

    Implements the bot's logic and encapsulates all the methods required for
    the bot operation.
    """

    def __init__(self, bot_dispatcher: BotDispatcher, flask_app: Optional[BotApp] = None):
        self._default_ok_response = {"ok": True}
        self.bot_dispatcher = bot_dispatcher
        self.bot_id = self.bot_dispatcher.user_id
        self.bot: TelegramBot = TelegramBot.query.get(self.bot_id)
        self.app = current_app if flask_app is None else flask_app

    def send_message(
        self, chat_id: int, text: Optional[str] = None, persist: bool = True, **kwargs
    ) -> Optional[TelegramMessage]:
        """Send a message to specified chat

        All arbitrary kwargs will be passed to an API call and processed if
        they have any meaning, or ignored otherwise.
        """
        msg: Optional[TelegramMessage] = None
        resp = self.bot_dispatcher.send_message(chat_id, text, **kwargs)
        if isinstance(resp, dict) and resp.get("ok", False) and resp.get("result", None):
            msg = TelegramMessage.from_dict(resp["result"], self.bot_id)
            if persist:
                msg.persist()
        else:
            self.app.logger.error(f"Error in response message: {resp}")
        return msg

    def process_update(self, update: dict) -> dict:
        """Process an incoming update"""
        message = update.get("message", None) or update.get("channel_post", None)
        if message:
            return self.process_message(message)
        return {"ok": True}

    def process_message(self, message: dict) -> dict:
        """Process an incoming message"""
        msg = TelegramMessage.from_dict(message, self.bot_id).persist()
        if msg.from_user and msg.from_user_id != self.bot_id:
            # Not an outgoing message and not a channel post
            # (channel posts have empty "from_user" field)
            if msg.chat_id:
                if msg.chat.type_code == "p":
                    return self.process_private_incoming_message(msg)
                if msg.chat.type_code in ("g", "s"):
                    return self.process_group_incoming_message(msg)
                if msg.chat.type_code == "c":
                    return self.process_channel_post(msg)
                self.app.logger.warn(
                    f"Unknown incoming message kind for message(bot_id={self.bot_id},"
                    f"chat_id={msg.chat_id}, message_id={msg.message_id})"
                )
        return self._default_ok_response

    def forward_message_to_chats(
        self, message: TelegramMessage, chats: List[TelegramChat]
    ) -> None:
        """Forward a message to specified chats"""
        for chat in chats:
            resp = self.bot_dispatcher.invoke_request(
                "forwardMessage",
                {
                    "chat_id": chat.id,
                    "from_chat_id": message.chat_id,
                    "disable_notification": False,
                    "message_id": message.message_id,
                },
            )
            try:
                msg = TelegramMessage.from_dict(resp["result"], self.bot_id)
                if msg.forward_from_id is None:
                    msg.forward_from_id = message.from_user_id
                msg.persist()
            except KeyError as exc:
                current_app.logger.exception(
                    f"An exception {type(exc).__name__} occurred while parsing the "
                    f"response. The response was: {resp}"
                )

    def forward_message_to_forward_chats(self, message: TelegramMessage) -> None:
        """Forward a message to the bot's designated forward chat"""
        if self.bot.chats_forward is not None:
            chats = [forward_chat.chat for forward_chat in self.bot.chats_forward]  # type: ignore
            self.forward_message_to_chats(message, chats)

    def process_private_incoming_message(self, message: TelegramMessage) -> dict:
        """Process private incoming message"""
        # self.bot_dispatcher.send_message(message.chat_id, message.get_markdown_v2_text())
        try:
            if message.from_user.is_subscriber(self.bot_id):
                if "/stop" in message.bot_commands:
                    message.from_user.unsubscribe(self.bot_id)
                    self.send_message(message.from_user.id, self.unsubscribe_message_text())
                elif "/start" in message.bot_commands:
                    self.send_message(message.from_user.id, self.already_subscribed_message_text())
                else:
                    self.send_message(
                        message.from_user.id, self.receive_confirmation_message_text()
                    )
                    self.forward_message_to_forward_chats(message)
            else:  # Not a subscriber
                if "/start" in message.bot_commands:
                    message.from_user.subscribe(self.bot_id)
                    self.send_message(message.from_user.id, self.subscribe_message_text())
                else:
                    self.send_message(
                        message.from_user.id, self.subscription_inactive_notify_text()
                    )
        except Exception as exc:  # pylint: disable=broad-except
            current_app.logger.exception(
                f"An exception {type(exc).__name__} occurred while processing "
                f"a private message."
            )
            # Try to send notification via bot. If the bot is totally dead,
            # at least we logged an exception earlier.
            if self.bot.chats_forward:
                chat: BotForwardChat
                for chat in self.bot.chats_forward:  # type: ignore
                    self.bot_dispatcher.send_message(
                        chat.chat_id,
                        f"An exception {type(exc).__name__} occurred "
                        "while processing a private message:\n{str(exc)}",
                    )
        return self._default_ok_response

    def process_group_incoming_message(self, message: TelegramMessage) -> dict:
        """Process group incoming message"""
        chat = message.chat

        if message.reply_to_message:
            if (
                message.reply_to_message.from_user
                and message.reply_to_message.from_user.id == self.bot_id
            ):
                return self.process_group_bot_reply(message)
        elif message.from_user and message.from_user.is_admin(self.bot_id):
            return self.process_group_admin_message(message)
        elif not chat.is_admin_channel(self.bot_id):
            # Handle other messages from channels here
            # self.send_message(message.chat_id, 'DEBUG (remove): Not an admin channel')
            pass
        return self._default_ok_response

    def process_group_admin_message(self, message: TelegramMessage) -> dict:
        """Process a message from admin posted in a group chat
        (not necessarily an admin group chat)"""
        if message.text:
            if message.text.startswith("/set_admin_channel"):
                try:
                    message.chat.set_admin_channel(self.bot_id)
                    self.send_message(message.chat.id, "Current chat is set as admin channel")
                except EInappropriateChatType as exc:
                    self.send_message(message.chat.id, exc.args[0])
            elif message.text.startswith("/revoke_admin_channel"):
                try:
                    message.chat.revoke_admin_channel(self.bot_id)
                    self.send_message(message.chat.id, "Current chat is unset as admin channel")
                except EInappropriateChatType as exc:
                    self.send_message(message.chat.id, exc.args[0])
            elif message.text.startswith("/set_forward_channel"):
                try:
                    message.chat.set_forward_channel(self.bot_id)
                    self.send_message(message.chat.id, "Current chat is set as forward channel")
                except EInappropriateChatType as exc:
                    self.send_message(message.chat.id, exc.args[0])
            elif message.text.startswith("/revoke_forward_channel"):
                try:
                    message.chat.revoke_forward_channel(self.bot_id)
                    self.send_message(message.chat.id, "Current chat is unset as forward channel")
                except EInappropriateChatType as exc:
                    self.send_message(message.chat.id, exc.args[0])
            elif message.text.startswith("/set_text "):
                splits = message.text.split(" ")
                code = splits[1].lower().strip()
                if code in [
                    "start",
                    "stop",
                    "receive_confirmation",
                    "already_sub",
                    "inactive_sub",
                ]:
                    BotReplyText.set_text(
                        bot_id=self.bot_id, code=code, text=" ".join((splits[2:]))
                    )
                    self.send_message(message.chat.id, "Set text successful")
                else:
                    self.send_message(
                        message.chat.id,
                        f'Unknown text code "{splits[1]}". I only recognize these codes:\n'
                        f"- start\n- stop\n- receive_confirmation\n- already_sub\n- inactive_sub",
                    )
            elif message.text.startswith("/get_text "):
                splits = message.text.split(" ")
                code = splits[1].lower().strip()
                if code in [
                    "start",
                    "stop",
                    "receive_confirmation",
                    "already_sub",
                    "inactive_sub",
                ]:
                    rec = BotReplyText.query.filter_by(bot_id=self.bot_id, code=code).first()
                    text = rec.text if rec else "*unspecified*"
                    self.send_message(message.chat.id, text)
                else:
                    self.send_message(
                        message.chat.id,
                        f'Unknown text code "{splits[1]}". I only recognize these codes:\n'
                        f"- start\n- stop\n- receive_confirmation\n- already_sub\n- inactive_sub",
                    )
            elif message.text.startswith("/id"):
                matches = re.findall(r"^\s*(/id)\s*\b(.*)", message.text, flags=re.DOTALL)
                if (
                    len(matches) >= 1
                    and isinstance(matches[0], tuple)
                    and (len(matches[0]) < 2 or matches[0][1].lower().strip() == "chat")
                ):
                    self.send_message(message.chat.id, str(message.chat.id))
            elif message.text.rstrip() == "/subs" and message.chat.is_admin_channel(self.bot_id):
                self.send_message(
                    message.chat.id, f"The current number of subscribers is {self.bot.sub_count}"
                )
            else:
                # Handle other messages from admin here
                # self.send_message(message.chat.id, 'DEBUG (remove): Message from admin user')
                pass
        return self._default_ok_response

    def process_group_bot_reply(self, message: TelegramMessage) -> dict:
        """Process a reply to the bot in a group"""
        if message.reply_to_message.forward_from:  # Reply to a forward by the bot
            if message.reply_to_message.forward_from.is_subscriber(self.bot_id):
                if not message.from_user or not message.from_user.is_admin(self.bot_id):
                    self.send_message(message.chat.id, "Only admins can reply to subscribers")
                elif not message.chat.is_admin_channel(
                    self.bot_id
                ) and not message.chat.is_forward_channel(self.bot_id):
                    self.send_message(
                        message.chat.id,
                        "Not an admin channel - message will not be forwarded to the subscriber",
                    )
                else:
                    self.send_message(
                        message.reply_to_message.forward_from.id,
                        message.get_markdown_v2_text(),
                        parse_mode="MarkdownV2",
                    )
                    self.send_message(message.chat.id, "I forwarded your reply to the subscriber")
            else:
                self.send_message(
                    message.chat.id, "Warning: reply to non-subscriber - will not be forwarded"
                )
        else:
            # Reply to the bot's message that isn't forwarded. Do nothing for now.
            pass
        return self._default_ok_response

    def process_channel_post(self, message: TelegramMessage) -> dict:
        """Process new channel post"""
        assert message is not None
        return self._default_ok_response

    def subscribe_message_text(self) -> str:
        """Return the currently configured reply for a new bot subscriber"""
        text_obj = BotReplyText.query.filter_by(bot_id=self.bot_id, code="start").first()
        return text_obj.text if text_obj else "Started"

    def unsubscribe_message_text(self) -> str:
        """Return the currently configured reply to unsubscribe request"""
        text_obj = BotReplyText.query.filter_by(bot_id=self.bot_id, code="stop").first()
        return text_obj.text if text_obj else "Stopped"

    def receive_confirmation_message_text(self) -> str:
        """Return the currently configured reply for an arbitrary PM to the bot
        from a subscriber"""
        text_obj = BotReplyText.query.filter_by(
            bot_id=self.bot_id, code="receive_confirmation"
        ).first()
        return text_obj.text if text_obj else "Noted"

    def already_subscribed_message_text(self) -> str:
        """Return the currently configured reply for when an already subscribed
        user issues another 'subscribe' command"""
        text_obj = BotReplyText.query.filter_by(bot_id=self.bot_id, code="already_sub").first()
        return text_obj.text if text_obj else "Already subscribed"

    def subscription_inactive_notify_text(self) -> str:
        """Return the currently configured reply for when a not currently subscribed
        user sends a message to the bot"""
        text_obj = BotReplyText.query.filter_by(bot_id=self.bot_id, code="inactive_sub").first()
        return (
            text_obj.text if text_obj else "Subscription is inactive. Send me /start to subscribe"
        )

    def set_commands(self, commands: List[BotCommand]) -> dict:
        """Set the list of the bot's supported commands

        Telegram bot API reference: https://core.telegram.org/bots/api#setmycommands
        """
        return self.bot_dispatcher.invoke_request(
            "setMyCommands", data={"commands": [c.to_dict() for c in commands]}
        )


def handle_update(bot_dispatcher: BotDispatcher, update: dict) -> dict:
    """Update processing entry point"""
    return UpdateHandler(bot_dispatcher).process_update(update)
