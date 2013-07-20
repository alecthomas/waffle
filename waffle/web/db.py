from injector import Module, inject, provides

from waffle.db import DatabaseSession
from waffle.web.flask import RequestTeardown


class DatabaseSessionModule(Module):
    """Manage SQLAlchemy session lifecycle."""

    @provides(RequestTeardown)
    @inject(session=DatabaseSession)
    def provide_db_request_teardown(self, session):
        def cleanup_db_session(exception):
            session.remove()

        return [cleanup_db_session]
