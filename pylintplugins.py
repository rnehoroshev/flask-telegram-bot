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
"""Pylint plugins"""
import logging
from typing import Any

from astroid import MANAGER, extract_node, scoped_nodes


def register(linter: Any) -> None:
    """Pylint plugin registration"""
    logging.info(
        "Registering pylint plugins module within linter %s (%s)",
        type(linter).__qualname__,
        linter.name,
    )


def transform(fnc: scoped_nodes.FunctionDef) -> None:
    """Transformation for FunctionDef node.

    Prevents false positives when accessing members of the (flask)app's logger properties
    """
    if fnc.name == "logger":
        for prop in ["debug", "info", "warning", "error", "handlers", "addHandler", "setLevel"]:
            fnc.instance_attrs[prop] = extract_node("def {name}(arg): return".format(name=prop))


MANAGER.register_transform(scoped_nodes.FunctionDef, transform)
