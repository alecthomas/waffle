import logging

from injector import Module, inject, provides
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from sqlalchemy.orm.session import Session

from waffle.flags import Flag, flag
from waffle.log import LogLevel


flag('--database_uri', help='Database URI [%(default)s].', metavar='URI')


# Re-exported for injector binding.
Session = Session

# Subclass models from this.
Base = declarative_base()


class DatabaseModule(Module):
    """Configure and initialize the ORM.

    - Requires the FlagsModule.
    - Uses the --database_uri flag.
    """

    @provides(Session)
    @inject(database_uri=Flag('database_uri'), log_level=LogLevel)
    def provide_db_session(self, database_uri, log_level):
        assert database_uri, '--database_uri not set, set a default in main() or run()'
        logging.getLogger('sqlalchemy.engine').setLevel(log_level)
        logging.info('Connecting to %s', database_uri)
        engine = create_engine(database_uri, convert_unicode=True)
        session = scoped_session(sessionmaker(autocommit=False,
                                              autoflush=False,
                                              bind=engine))
        Base.query = session.query_property()
        Base.metadata.create_all(bind=engine)
        return session
