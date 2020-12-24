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
"""Unit tests"""
import unittest

from flask.ctx import AppContext

from app import create_app, db
from common import EInvalidEmailAddress, email_list
from config import Config
from telegram_bot import BotDispatcher


class TestConfig(Config):  # pylint: disable=too-few-public-methods
    """Test config"""

    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"


class FlaskTelegramBotAppTestCase(unittest.TestCase):
    """Base class for common test cases"""

    def shortDescription(self):
        """Disable test docstring output"""
        return None

    def setUp(self):
        """Set up test"""
        self.app = create_app(TestConfig)
        self.app_context = self.app.app_context()  # type: AppContext
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        """Tear down test"""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()


class EmailAddressParserCase(FlaskTelegramBotAppTestCase):
    """Email address parser test case"""

    def test_email_list_raises_typeerror(self):
        """Test that email_list() will raise TypeError when passing an invalid argument"""
        with self.assertRaises(TypeError):
            # noinspection PyTypeChecker
            email_list(None)

    def test_email_list_raises_invalid_email_address(self):
        """Test that email_list() will raise EInvalidEmailAddress"""
        with self.assertRaises(EInvalidEmailAddress):
            email_list("John Doe <john#doe@example.com>")

    def test_email_list_parse_single_email_address(self):
        """Test parsing a single email address without name part"""
        email_str = "johndoe@example.com"
        emails = email_list(email_str)
        self.assertIsInstance(emails, list)
        self.assertEqual(len(emails), 1)
        self.assertIsInstance(emails[0], tuple)
        self.assertIs(emails[0][0], None)
        self.assertEqual(emails[0][1], "johndoe@example.com")

    def test_email_list_parse_single_email_address_with_sender_name(self):
        """Test parsing a single email address with name part"""
        test_input = "john.doe@example.com"
        emails = email_list(test_input)
        self.assertIsInstance(emails, list)
        self.assertEqual(len(emails), 1)
        self.assertIsInstance(emails[0], tuple)
        self.assertIs(emails[0][0], None)
        self.assertEqual(emails[0][1], "john.doe@example.com")

        test_input = "'John Doe' <john_doe@example.com>"
        emails = email_list(test_input)
        self.assertIsInstance(emails, list)
        self.assertEqual(len(emails), 1)
        self.assertIsInstance(emails[0], tuple)
        self.assertEqual(emails[0][0], "'John Doe'")
        self.assertEqual(emails[0][1], "john_doe@example.com")

        test_inputs = [
            "John Doe johndoe@example.com",
            '"John Doe" johndoe@example.com',
            "John Doe <johndoe@example.com>",
            '"John Doe" <johndoe@example.com>',
        ]
        for test_input in test_inputs:
            emails = email_list(test_input)
            self.assertIsInstance(emails, list)
            self.assertEqual(len(emails), 1)
            self.assertIsInstance(emails[0], tuple)
            self.assertEqual(emails[0][0], "John Doe")
            self.assertEqual(emails[0][1], "johndoe@example.com")

    def test_email_list_parse_number_of_email_addresses(self):
        """Test parsing a list of email addresses in many different supported formats"""
        test_input = (
            "johndoe@example.com; Jane Doe <jane_doe@example.com>;"
            'Jim <jim-doe@example.com;"Jared Doe" jared_doe@example.com'
        )
        emails = email_list(test_input)
        self.assertIsInstance(emails, list)
        self.assertEqual(len(emails), 4)
        self.assertIsInstance(emails[0], tuple)
        self.assertIsInstance(emails[1], tuple)
        self.assertIsInstance(emails[2], tuple)
        self.assertIsInstance(emails[3], tuple)
        self.assertIs(emails[0][0], None)
        self.assertEqual(emails[0][1], "johndoe@example.com")
        self.assertEqual(emails[1][0], "Jane Doe")
        self.assertEqual(emails[1][1], "jane_doe@example.com")
        self.assertEqual(emails[2][0], "Jim")
        self.assertEqual(emails[2][1], "jim-doe@example.com")
        self.assertEqual(emails[3][0], "Jared Doe")
        self.assertEqual(emails[3][1], "jared_doe@example.com")


class BotDispatcherCase(FlaskTelegramBotAppTestCase):
    """Bot dispatcher test case"""

    def test_app_dispatcher_token(self):
        """Test that flask app instance has a valid dispatcher attribute
        with the configured bot token"""
        self.assertIsInstance(self.app.bot_dispatcher, BotDispatcher)
        self.assertEqual(self.app.bot_dispatcher.token, self.app.config["BOT_TOKEN"])

    def test_simple_api_request(self):
        """Test sending a simple API request and receiving a valid response"""
        response = self.app.bot_dispatcher.invoke_request("getMe")
        self.assertIsInstance(response, dict)
        self.assertIn("ok", response)


if __name__ == "__main__":
    unittest.main(verbosity=2)
