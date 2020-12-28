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
"""Handlers for incoming bot updates"""
import importlib
import inspect
import os
import pkgutil
from inspect import Parameter, getmembers, isfunction
from types import ModuleType
from typing import NamedTuple, Sequence

from telegram_bot import BotDispatcher


class ParamDescription(NamedTuple):
    """A prettier variant of a function parameter description as returned by
    :meth:`inspect.signature(func).parameters`
    """

    name: str
    param: Parameter


class ModuleMemberDescription(NamedTuple):
    """A prettier variant of a module member description as returned by
    :meth:`inspect.getmembers(module)`
    """

    name: str
    member: object


def register_handlers(bot: BotDispatcher, handler_modules: Sequence[str]) -> Sequence[str]:
    """Search for a valid bot handler modules and register them within the bot dispatcher"""
    modules = []
    package_path: str = os.path.dirname(__file__)
    package_modules = list(
        [name for _, name, _ in pkgutil.iter_modules([package_path]) if name in handler_modules]
    )
    for module_name in handler_modules:
        if module_name in package_modules:
            module = importlib.import_module(f".{module_name}", __package__)
            modules.extend(try_register_handler_module(bot, module))
    return modules


def try_register_handler_module(bot: BotDispatcher, module: ModuleType) -> list:
    """Checks if a given module is a valid bot handler, and if so, registers it"""
    for func_name, func in getmembers(module, isfunction):
        if func_name == "handle_update":
            sig = inspect.signature(func)
            if (params := list(sig.parameters.items())) and len(params) >= 2:
                first_param = ParamDescription(*params[0])
                second_param = ParamDescription(*params[1])
                if (
                    first_param.name == "bot_dispatcher"
                    and first_param.param.annotation in (Parameter.empty, BotDispatcher)
                    and second_param.name == "update"
                    and second_param.param.annotation in (Parameter.empty, dict)
                ):
                    bot.receive_update(func)
                    return [module.__name__]
    return []
