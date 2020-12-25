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
"""Bot blueprint exceptions"""
from typing import Any, Optional


class EInvalidToken(Exception):
    """Invalid bot token"""


class EInvalidUpdateFormat(Exception):
    """Invalid/unknown update format"""

    def __init__(
        self,
        message: Optional[str] = None,
        response_mimetype: Optional[str] = None,
        response_length: Optional[int] = None,
        response_data: Optional[Any] = None,
        **kwargs,
    ):
        self.response_mimetype = response_mimetype
        self.response_length = response_length
        self.response_data = response_data
        self.message = message
        super().__init__(
            dict(
                **kwargs,
                **{
                    "message": message,
                    "response_mimetype": response_mimetype,
                    "response_length": response_length,
                    "response_data": response_data,
                },
            )
        )
