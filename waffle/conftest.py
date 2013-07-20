from __future__ import absolute_import

import logging
import tempfile

import pytest
from injector import Injector, Module
from sqlalchemy import Column, Integer, String, ForeignKey

from waffle.db import DatabaseModule, DatabaseEngine, DatabaseSession, Base
from waffle.flags import Flag


class TestingModule(Module):
    def __init__(self, tmpfile):
        self.tmpfile = tmpfile

    def configure(self, binder):
        print self.tmpfile
        binder.bind(Flag('database_uri'), to='sqlite:///%s' % self.tmpfile)
        binder.bind(Flag('database_pool_size'), to=0)
        logging.getLogger('sqlalchemy.engine').setLevel(logging.DEBUG)


class User(Base):
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(20))
    friend = ForeignKey(Integer, 'User')


@pytest.fixture
def db(request):
    self = request.instance

    tmpfile = tempfile.NamedTemporaryFile(prefix='waffle_db_test.sqlite.')

    injector = Injector([DatabaseModule, TestingModule(tmpfile.name)])
    engine = injector.get(DatabaseEngine)
    session = injector.get(DatabaseSession)

    self.session = session

    @request.addfinalizer
    def finalize_session():
        session.remove()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()
        tmpfile.close()

    return session
