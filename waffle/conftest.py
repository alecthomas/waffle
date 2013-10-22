from __future__ import absolute_import

import logging

import pytest
from injector import Injector, Module
from sqlalchemy import Column, Integer, String, ForeignKey

from waffle.db import DatabaseModule, DatabaseEngine, DatabaseSession, Model
from waffle.flags import FlagKey


class TestingModule(Module):
    def configure(self, binder):
        binder.bind(FlagKey('database_uri'), to='postgresql://localhost:5432/waffle')
        binder.bind(FlagKey('database_pool_size'), to=0)
        logging.getLogger('sqlalchemy.engine').setLevel(logging.DEBUG)


class User(Model):
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(20))
    friend = ForeignKey(Integer, 'User')


@pytest.fixture
def db(request):
    self = request.instance

    injector = Injector([DatabaseModule, TestingModule()])
    engine = injector.get(DatabaseEngine)
    session = injector.get(DatabaseSession)

    self.session = session

    @request.addfinalizer
    def finalize_session():
        session.remove()
        Model.metadata.drop_all(bind=engine)
        engine.dispose()

    return session
