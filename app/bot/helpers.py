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
"""Bot blueprint helpers"""
from typing import Dict

from flask import Response, jsonify

default_ok_dict_response: Dict[str, bool] = {"ok": True}


def default_ok_response() -> Response:
    """Return default 'ok' response"""
    resp = jsonify(default_ok_dict_response)
    resp.headers["Content-Type"] = "application/json"
    resp.status_code = 200
    return resp


def error_response(msg: str, status_code: int = 500, **kwargs) -> Response:
    """Construct a valid error response"""
    response_payload = {"ok": False, "error": msg}
    for key, value in kwargs.items():
        response_payload[key] = value
    response = jsonify(response_payload)
    response.headers["Content-Type"] = "application/json"
    response.status_code = status_code
    return response
