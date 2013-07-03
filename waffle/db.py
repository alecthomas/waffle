import logging

from injector import Module, inject, provides, singleton
from sqlalchemy.engine import Engine as DatabaseEngine
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.declarative import AbstractConcreteBase, declarative_base, declared_attr
from sqlalchemy import create_engine
from sqlalchemy.orm.session import Session as DatabaseSession

from waffle.flags import Flag, flag
from waffle.log import LogLevel


flag('--database_uri', help='Database URI.', metavar='URI')
flag('--database_logging', help='Log database operations.', action='store_true')


# Re-exported for injector binding.
DatabaseSession = DatabaseSession

# Subclass models from this.
_Base = declarative_base()


class Base(_Base, AbstractConcreteBase):
    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower()

    @property
    def query_self(self):
        return self.query.filter(self.__class__.id == self.id)


class DatabaseModule(Module):
    """Configure and initialize the ORM.

    - Requires the FlagsModule.
    - Uses the --database_uri flag.
    """

    @singleton
    @provides(DatabaseEngine)
    @inject(database_uri=Flag('database_uri'), database_logging=Flag('database_logging'), log_level=LogLevel)
    def provide_db_engine(self, database_uri, database_logging, log_level):
        assert database_uri, '--database_uri not set, set a default in main() or run()'
        if database_logging:
            logging.getLogger('sqlalchemy.engine').setLevel(log_level)
        logging.info('Connecting to %s', database_uri)
        engine = create_engine(database_uri, convert_unicode=True)
        return engine

    @singleton
    @provides(DatabaseSession)
    @inject(engine=DatabaseEngine)
    def provide_db_session(self, engine):
        session = scoped_session(sessionmaker(autocommit=False,
                                              autoflush=False,
                                              bind=engine))
        Base.query = session.query_property()
        Base.metadata.create_all(bind=engine)
        return session
