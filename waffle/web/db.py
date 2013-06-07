from injector import Module, inject, provides

from waffle.db import Session
from waffle.web import RequestTeardown


class DatabaseSessionModule(Module):
    """Manage SQLAlchemy session lifecycle."""

    @provides(RequestTeardown)
    @inject(session=Session)
    def provide_db_request_teardown(self, session):
        return [session.close]
