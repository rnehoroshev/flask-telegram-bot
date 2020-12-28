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
"""Application-wide database and migration objects"""
from typing import TYPE_CHECKING, Type

from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import BigInteger
from sqlalchemy.dialects import mysql, postgresql, sqlite

db = SQLAlchemy()
migrate = Migrate()

if TYPE_CHECKING:
    from app.models import AppModel  # pylint: disable=ungrouped-imports

    BaseModel: Type[AppModel] = db.make_declarative_base(AppModel)
else:
    BaseModel = db.Model

# Fix auto-incrementing BIGINT primary keys for SQLite
# https://stackoverflow.com/a/23175518/5418628
BigIntegerType = (
    BigInteger()
    .with_variant(postgresql.BIGINT(), "postgresql")
    .with_variant(mysql.BIGINT(), "mysql")
    .with_variant(sqlite.INTEGER(), "sqlite")
)


class PersistableMixin:  # pylint: disable=too-few-public-methods
    """A helper to quickly persist an object

    This is just a syntactic sugar to lazily call `session.commit`.
    When using it, keep in mind that it will immediately finish the currently active
    transaction, committing all the pending updates. If used carelessly, it can leave
    the data in an inconsistent state.
    """

    def persist(self):
        """Commits all the changed objects in session and finishes the currently active
        transaction"""
        db.session.merge(self)
        db.session.commit()
        return self
