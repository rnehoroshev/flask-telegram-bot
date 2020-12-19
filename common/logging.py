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
"""Additional logging formatters and utilities"""
import os
from logging import Formatter, LogRecord
from typing import Optional


class RelativePathsFormatter(Formatter):
    """Log record formatter with relative source code file path support

    Usage is similar to standard :class:`logging.Formatter`. Introduces an additional 'relpath'
    format token that represents the relative path to the the source file in which logging event
    occurred. To indicate the base path to which relative paths will be evaluated, pass
    ``paths_relative_to`` argument to the constructor. If not set, the token will render itself
    as an absolute path, similar to the standard token 'pathname'.
    """

    def __init__(
        self,
        fmt: Optional[str] = None,
        datefmt: Optional[str] = None,
        style: str = "%",
        validate: bool = True,
        paths_relative_to: Optional[str] = None,
    ):  # pylint: disable=too-many-arguments
        """
        Initialize the formatter with specified format strings.
        """
        self.paths_relative_to = (
            paths_relative_to if isinstance(paths_relative_to, str) else os.path.abspath(os.sep)
        )
        super().__init__(fmt, datefmt, style, validate)

    def formatMessage(self, record: LogRecord) -> str:
        """
        Format the specified record as text message.
        """
        cpfx = os.path.commonprefix((record.pathname, self.paths_relative_to))
        if not cpfx or (cpfx == os.path.abspath(os.sep)) or (cpfx != self.paths_relative_to):
            relpath = record.pathname
        else:
            relpath = os.path.relpath(record.pathname, self.paths_relative_to)
        record.__dict__["relpath"] = relpath
        return super().formatMessage(record)
