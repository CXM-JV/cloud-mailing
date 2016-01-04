# Copyright 2015 Cedric RICARD
#
# This file is part of mf.
#
# mf is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# mf is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with mf.  If not, see <http://www.gnu.org/licenses/>.

from twisted.internet.defer import returnValue
from twisted.internet import defer
from txmongo.connection import ConnectionPool

from . import settings
from .singletonmixin import Singleton

__author__ = 'Cedric RICARD'


class Db(Singleton):
    _pool = None

    def __init__(self, db_name, pool_size=10):
        self._pool = ConnectionPool(pool_size=10)
        self._db = self.pool[db_name]

    @staticmethod
    def disconnect():
        if Db.isInstantiated:
            return Db.getInstance()._pool.disconnect()

    @property
    def pool(self):
        return self._pool

    @property
    def db(self):
        return self._db

    # # @defer.inlineCallbacks
    # def get_master_db(self):
    #     # mongo = yield get_db_connection()
    #     # returnValue(getattr(mongo, settings.MASTER_DATABASE))
    #     return getattr(self._pool, settings.MASTER_DATABASE)


def get_db():
    return Db.getInstance().db