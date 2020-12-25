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
"""Telegram bot dispatcher encapsulates methods for communicating with the Telegram Bot API"""
import json
from typing import Any, Callable, ClassVar, List, Union

import requests

from .exceptions import EInvalidBotToken, ETelegramAPIError


class BotDispatcher:
    """The bot dispatcher responsible for issuing Telegram Bot API requests and passing
    responses to response handlers"""

    _api_endpoint_template: ClassVar[str] = "https://api.telegram.org/bot{token}/{method}"
    _bots: ClassVar[dict] = dict()

    @classmethod
    def get(cls, token: str) -> "BotDispatcher":
        """Returns a :class:`BotDispatcher` instance for a bot identified by the given token"""
        return cls._bots.get(token, cls(token))

    def __init__(self, token: str):
        self.token = token
        self.update_handlers: List = []
        BotDispatcher._bots[token] = self

    @property
    def token(self) -> str:
        return self._token

    @token.setter
    def token(self, value: str) -> None:
        try:
            self.user_id = int(value.split(":")[0])
        except Exception as exc:
            raise EInvalidBotToken("Invalid bot token", value) from exc
        self._token = value

    def endpoint(self, method: str) -> str:
        """Returns a fully constructed endpoint for a given method with current bot's token"""
        return self._api_endpoint_template.format(token=self.token, method=method)

    def invoke_request(self, method: str, data: dict = None) -> dict:
        """Calls an arbitrary API method and returns server answer"""
        r = requests.post(self.endpoint(method), json=data)
        try:
            d = json.loads(r.text)
        except json.JSONDecodeError as exc:
            raise ETelegramAPIError("Error parsing API response", r.text) from exc
        return d

    def send_message(self, chat_id: int, text: str, **kwargs) -> dict:
        """Sends a message to the specified chat

        All arbitrary kwargs will be passed to API call and
        processed if they have any meaning, or ignored otherwise.
        """
        message = dict({"chat_id": chat_id, "text": text}, **kwargs)
        return self.invoke_request("sendMessage", data=message)

    def process_update(self, data: dict) -> dict:
        """Processes an incoming bot update by calling all the update handlers

        An update handler is a callable that accepts an update object (a :class:`dict` instance)
        and is expected to return either a dictionary with "ok" key, or an arbitrary value that
        will be treated as a boolean. If said value evaluates to False, further processing of
        update is stopped, otherwise the next handler is called. The handlers are called in the
        order in which they were added using the :meth:`BotDispatcher.receive_update` decorator.
        """
        result = dict()
        for f in self.update_handlers:
            f_result: Any = f(data)
            result[".".join((f.__module__, f.__qualname__))] = f_result
            if not f_result or (isinstance(f_result, dict) and f_result["ok"] is not True):
                break
        return result

    @property
    def receive_update(self) -> Callable[[Callable], None]:
        """Decorator that subscribes a decorated function to receiving incoming bot updates"""

        def decorator(f: Callable) -> None:
            self.update_handlers.append(f)

        return decorator

    def __reduce__(self) -> Union[str, tuple]:
        """Helper method for pickle"""
        return self.__class__, (self.token,)
