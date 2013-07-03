from injector import Module, inject, provides

from waffle.db import Session
from waffle.web.flask import RequestTeardown


class DatabaseSessionModule(Module):
    """Manage SQLAlchemy session lifecycle."""

    @provides(RequestTeardown)
    @inject(session=Session)
    def provide_db_request_teardown(self, session):
        def cleanup(exception):
            if exception:
                session.rollback()
            else:
                session.commit()
            session.remove()

        return [cleanup]
