import logging
from functools import wraps

from injector import Module, inject, provides, singleton
from sqlalchemy.engine import Engine as DatabaseEngine
from sqlalchemy.orm import sessionmaker, class_mapper
from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy import create_engine
from sqlalchemy.exc import InvalidRequestError
from sqlalchemy.orm.exc import UnmappedClassError
from sqlalchemy.orm.session import Session
from sqlalchemy.util import ThreadLocalRegistry

from waffle.flags import Flag, flag


flag('--database_uri', help='Database URI.', metavar='URI')
flag('--database_pool_size', help='Database connection pool size.', metavar='N', default=5)


DatabaseSession = Session


class NestedSession(Session):
    def __init__(self, *args, **kwargs):
        super(NestedSession, self).__init__(*args, **kwargs)
        self._depth = 0

    def __enter__(self):
        self._depth += 1
        self.begin(subtransactions=True)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is None:
            self.flush()
            self.commit()
        else:
            self.rollback()
        self._depth -= 1


class SessionManager(object):
    """A thread-safe session manager.

    This provides the following semantics:

    - Sessions are started via a contextmanager.
    - Entering a Session context opens a transaction and returns a session recursively.
    - Provides a query_property that can only be used within a transaction.
    """

    def __init__(self, session_factory):
        self._session_factory = session_factory
        self._registry = ThreadLocalRegistry(session_factory)

    def __enter__(self):
        if not self._registry.has():
            sess = self._session_factory()
            self._registry.set(sess)
        return self._registry().__enter__()

    def __exit__(self, exc_type, exc_value, traceback):
        if self._registry.has():
            sess = self._registry()
            sess.__exit__(exc_type, exc_value, traceback)

    def remove(self):
        """Close the associated session and disconnect."""
        if self._registry.has():
            self._registry().close()
        self._registry.clear()

    def query_property(self, query_cls=None):
        class query(object):
            def __get__(s, instance, owner):
                try:
                    mapper = class_mapper(owner)
                    if mapper:
                        if not self._registry.has() or not self._registry()._depth:
                            raise InvalidRequestError('Cannot access %s.query outside transaction' % owner.__name__)
                        if query_cls:
                            # custom query class
                            return query_cls(mapper, session=self._registry())
                        else:
                            # session's configured query class
                            return self._registry().query(mapper)
                except UnmappedClassError:
                    return None
        return query()

    def __getattr__(self, name):
        """Proxy all attribute access to current session."""
        if not self._registry.has():
            raise InvalidRequestError('No transaction is active, use with session: ...')
        return getattr(self._registry(), name)


class _Base(object):
    @declared_attr
    def __tablename__(cls):
        return cls.__name__

    @property
    def session(self):
        """Get the session associated with this model instance."""
        return self.query.session

    def save(self):
        """Add the object to the session for update."""
        self.session.add(self)
        return self

    @property
    def query_self(self):
        return self.query.filter(self.__class__.id == self.id)

    def __repr__(self):
        def reprs(cls):
            attrs = {}
            for col in cls.__table__.c:
                attrs[col.name] = repr(getattr(self, col.name))
            mapper_args = getattr(cls, '__mapper_args__', {})
            polymorphic_on = mapper_args.get('polymorphic_on', None)
            if polymorphic_on is not None:
                del attrs[polymorphic_on.name]
            return attrs

        def mro_reprs(inst):
            cls = inst.__class__
            attrs = {}
            for base in cls.__mro__:
                if hasattr(base, '__table__'):
                    attrs.update(reprs(base))
            return attrs

        def format(attrs):
            for key, value in sorted(attrs.items()):
                yield '%s=%s' % (key, value)

        cls_name = type(self).__name__
        return '%s(%s)' % (cls_name, ', '.join(format(mro_reprs(self))))


Base = declarative_base(cls=_Base)


class DatabaseModule(Module):
    """Configure and initialize the ORM.

    - Requires the FlagsModule.
    - Uses the --database_uri flag.
    - Provides DatabaseSession, a thread safe factory for SQLAlchemy sessions.
    """

    @provides(DatabaseEngine, scope=singleton)
    @inject(database_uri=Flag('database_uri'), database_pool_size=Flag('database_pool_size'))
    def provide_db_engine(self, database_uri, database_pool_size):
        assert database_uri, '--database_uri not set, set a default in main() or run()'
        logging.info('Connecting to %s', database_uri)
        extra_args = {}
        if not database_uri.startswith('sqlite:'):
            extra_args['pool_size'] = database_pool_size
        engine = create_engine(database_uri, convert_unicode=True, **extra_args)
        return engine

    @provides(DatabaseSession, scope=singleton)
    @inject(engine=DatabaseEngine)
    def provide_db_session(self, engine):
        session = SessionManager(sessionmaker(autocommit=True,
                                              autoflush=True,
                                              bind=engine,
                                              class_=NestedSession))
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
    if isinstance(thing, (NestedSession, SessionManager)):
        return thing

    if isinstance(thing, Base) or type(thing) is type:
        return thing.query.session

    @wraps(thing)
    def wrapper(self, *args, **kwargs):
        with self._session:
            return thing(self, *args, **kwargs)

    return wrapper
