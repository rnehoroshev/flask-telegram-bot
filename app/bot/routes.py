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
"""Bot web application endpoints"""
import json
import os
from typing import TYPE_CHECKING, Optional

from flask import Response, current_app, jsonify, request

from .exceptions import EInvalidUpdateFormat
from .helpers import default_ok_response, error_response

if TYPE_CHECKING:
    from . import TelegramBotBlueprint


def register_routes(blueprint: "TelegramBotBlueprint"):
    """Register routes within the blueprint"""

    @blueprint.route("/receive_update", methods=["GET", "POST"])
    def receive_update() -> Response:  # pylint: disable=unused-variable
        """Incoming update handler

        This endpoint should be registered with Telegram Bot API's 'setWebhook' method.
        Telegram will send a POST request with update object to this endpoint. It expects
        a JSON object with "ok" attribute in response.

        It is advised to respond ASAP to indicate that our bot received the update and is
        going to process it. The actual processing may occur independently.

        Updates API reference: https://core.telegram.org/bots/api#getting-updates
        """
        if request.method == "POST":
            # ToDo: start processing in a separate thread
            try:
                try:
                    json_payload = json.dumps(request.json, ensure_ascii=False).encode("utf8")
                    if TYPE_CHECKING:
                        assert isinstance(request.json, dict)
                    update_id = request.json["update_id"]
                except (json.JSONDecodeError, KeyError) as exc:
                    response_mimetype: Optional[str] = request.content_type
                    response_length: int = request.content_length or 0
                    if response_length < 1024 ** 2:
                        response_data: Optional[str] = request.get_data().decode()
                        response_data_sample: str = str(response_data)[:500]
                    else:
                        response_data = None
                        response_data_sample = "(Unavailable - response is too big)"
                    raise EInvalidUpdateFormat(
                        f'An update has invalid format. Content-type: "{response_mimetype}"; '
                        f'Length: {response_length}; Data: "{response_data_sample}'
                        f'{"..." if response_length > 500 else ""}"',
                        response_mimetype=response_mimetype,
                        response_length=response_length,
                        response_data=response_data,
                    ) from exc
            except EInvalidUpdateFormat:
                error_text = "Error parsing incoming telegram update data"
                current_app.logger.exception(error_text)
                return error_response(error_text)  # Should we respond with an error here?
                # If Telegram won't receive an "ok" response, it will keep retrying
                # sending the update, hitting the same wall indefinitely. We should
                # probably just log this update as an error, dump it for further examination,
                # notify bot maintainers and move on.

            try:
                current_app.logger.debug(
                    f"Incoming update ID={update_id}, payload={json_payload.decode()}",
                )
                if current_app.config["DUMP_UPDATES"]:
                    json_payload_pp = json.dumps(
                        request.json, ensure_ascii=False, indent=4
                    ).encode("utf8")
                    filename = os.path.join(
                        current_app.config["UPDATES_DUMP_DIR"], f"{update_id}.json"
                    )
                    with open(filename, "w", encoding="utf8") as update_file:
                        update_file.write(json_payload_pp.decode())
                blueprint.bot_dispatcher.process_update(request.json)
            except Exception as exc:  # pylint: disable=broad-except
                current_app.logger.exception(
                    f"An exception {type(exc).__name__} occurred while processing "
                    f"update {update_id}"
                )
        return default_ok_response()

    @blueprint.route("/about")
    def about() -> Response:  # pylint: disable=unused-variable
        """Return information about the bot"""
        return jsonify(blueprint.bot_dispatcher.invoke_request("getMe"))
