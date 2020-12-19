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
"""Common and helper routines"""
import re
from typing import List, NamedTuple

name_and_email_regex = re.compile(
    r'(?:"?([^"<]+)"?\s)?(?:<?([A-Za-z0-9_\-.]+@[A-Za-z0-9_\-.]+)>?)'
)


class EmailAddress(NamedTuple):
    """Email address"""

    name: str
    email: str


class EInvalidEmailAddress(Exception):
    """Invalid email address"""

    def __init__(self, email_address: str = None, message: str = None, **kwargs):
        self.message = message if isinstance(message, str) else "Invalid email address"
        self.email_address = email_address
        super().__init__(dict(**kwargs, **{"email_address": email_address, "message": message}))

    def __str__(self):
        return (
            ": ".join((self.message, self.email_address))
            if isinstance(self.email_address, str)
            else self.message
        )


def email_list(email_string: str, delimiter: str = ";") -> List[EmailAddress]:
    """Splits a string with email addresses into list of (name, email) tuples.

    An input string is treated as character-separated list of email addresses.
    Each address can include an optional sender name component. If sender name
    is present, it should be placed before the address. It may or may not be
    double-quoted. Email address may or may not be enclosed in '<>' brackets.

    :param email_string: Input strings
    :param delimiter: Delimiter character. Optional, default is semicolon (';')
    :raise TypeError: If argument is not a string
    :raise EInvalidEmailAddress: If argument or one of its components is not a valid email address
    :return: List of tuples (name, email). Name component can be None

    :Example:
    >>> email_list(
        'John Doe <johndoe@example.com>; "Jane Doe" jane.doe@example.com; nobody@example.com')
    [
        ('John Doe', 'johndoe@example.com'),
        ('Jane Doe', 'jane.doe@example.com'),
        (None, 'nobody@example.com')
    ]
    """
    if not isinstance(email_string, str):
        raise TypeError(
            f"Wrong argument type for email_list() call. Expected str, "
            f"got {email_string.__class__.__name__}"
        )

    last_parsed_string = email_string
    try:
        result = [
            EmailAddress(
                *name_and_email_regex.match(
                    last_parsed_string := email_string.strip()  # type: ignore
                ).groups()
            )
            for email_string in email_string.split(delimiter)
        ]
    except AttributeError as exc:
        raise EInvalidEmailAddress(last_parsed_string) from exc

    return result
