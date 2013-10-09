from __future__ import absolute_import

from injector import Module, inject, provides
from clastic import Middleware

from waffle.db import DatabaseSession
from waffle.web.clastic import Middlewares


class SQLAlchemyMiddleware(Middleware):
    def __init__(self, session):
        self._session = session

    def request(self, next, _route):
        if hasattr(_route.endpoint, '__transaction__'):
            with self._session:
                return next()
        else:
            try:
                return next()
            finally:
                self._session.remove()


class DatabaseSessionModule(Module):
    """Manage SQLAlchemy session lifecycle."""

    @provides(Middlewares)
    @inject(session=DatabaseSession)
    def provide_db_middleware(self, session):
        return [SQLAlchemyMiddleware(session)]
