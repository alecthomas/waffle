import logging
from functools import wraps

from injector import Module, inject, provides, singleton
from sqlalchemy.engine import Engine as DatabaseEngine
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy import create_engine
from sqlalchemy.orm.session import Session as DatabaseSession

from waffle.flags import Flag, flag


flag('--database_uri', help='Database URI.', metavar='URI')
flag('--database_pool_size', help='Database connection pool size.', metavar='N', default=5)


DatabaseSession = DatabaseSession


# Subclass models from this.
class _Base(object):
    @declared_attr
    def __tablename__(cls):
        return cls.__name__

    def save(self):
        self.query.session.add(self)
        return self

    @property
    def query_self(self):
        return self.query.filter(self.__class__.id == self.id)

    def __repr__(self):
        def reprs(cls):
            for col in cls.__table__.c:
                yield col.name, repr(getattr(self, col.name))
            mapper_args = getattr(cls, '__mapper_args__', None)
            if mapper_args:
                parent = mapper_args.get('inherits', None)
                if parent:
                    for n in reprs(parent):
                        yield n

        def format(attrs):
            for key, value in sorted(attrs.items()):
                yield '%s=%s' % (key, value)

        cls_name = type(self).__name__
        return '%s(%s)' % (cls_name, ', '.join(format(dict(reprs(self)))))


Base = declarative_base(cls=_Base)


class DatabaseModule(Module):
    """Configure and initialize the ORM.

    - Requires the FlagsModule.
    - Uses the --database_uri flag.
    - Provides DatabaseSessionFactory, a function that provides SQLAlchemy sessions.
    """

    @provides(DatabaseEngine, scope=singleton)
    @inject(database_uri=Flag('database_uri'), database_pool_size=Flag('database_pool_size'))
    def provide_db_engine(self, database_uri, database_pool_size):
        assert database_uri, '--database_uri not set, set a default in main() or run()'
        logging.info('Connecting to %s', database_uri)
        engine = create_engine(database_uri, convert_unicode=True, pool_size=database_pool_size)
        return engine

    @singleton
    @provides(DatabaseSession)
    @inject(engine=DatabaseEngine)
    def provide_db_session(self, engine):
        session = scoped_session(sessionmaker(autocommit=False,
                                              autoflush=True,
                                              bind=engine))
        Base.query = session.query_property()
        Base.metadata.create_all(bind=engine)
        return session


def transaction(thing):
    """A general-purpose transaction helper.

    Can be used with a session-like object:

        with transaction(session):
            ...

    With objects/classes derived from Base:

        with transaction(user):
            ...

        with transaction(User):
            ...

    As a method decorator (assumes self has a _session attribute):

        @transaction
        def method(self, ...):
            ...
    """
    if isinstance(thing, (scoped_session, DatabaseSession)):
        return thing.begin(subtransactions=True)

    if isinstance(thing, Base) or type(thing) is type:
        return thing.query.session.begin(subtransactions=True)

    @wraps(thing)
    def wrapper(self, *args, **kwargs):
        with self._session.begin(subtransactions=True):
            return thing(self, *args, **kwargs)

    return wrapper
