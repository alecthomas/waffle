import threading

import pytest
from sqlalchemy.exc import InvalidRequestError

from waffle.conftest import User


@pytest.mark.usefixtures('db')
class TestDatabaseSessionManager(object):
    def test_can_not_save_outside_context_manager(self):
        with pytest.raises(InvalidRequestError):
            User(name='bob').save()

    def test_can_not_save_outside_context_manager_after_session_creation(self):
        with self.session:
            User(name='bob').save()

        with pytest.raises(InvalidRequestError):
            User.query.count()

    def test_can_save_within_context_manager(self):
        with self.session:
            User(name='bob').save()
            assert User.query.count() == 1

    def test_can_not_query_outside_context_manager(self):
        with self.session:
            User(name='bob').save()

        with pytest.raises(InvalidRequestError):
            User.query.count()

    def test_can_query_within_context_manager(self):
        with self.session:
            User(name='bob').save()

        with self.session:
            assert User.query.count() == 1

    def test_can_query_object_from_parent_transaction_when_nested(self):
        with self.session as session:
            User(name='bob').save()

            with session:
                assert User.query.count() == 1

        with self.session:
            assert User.query.count() == 1

    def test_object_remains_associated_across_transactions(self):
        with self.session:
            bob = User(name='bob').save()

        with self.session:
            assert User.query.count() == 1
            User(name='fred', friend=bob).save()

        with self.session:
            assert User.query.count() == 2

    def _thread_is_not_in_session(self, event):
        with pytest.raises(InvalidRequestError):
            User(name='bob').save()
        with self.session:
            User(name='bob').save()
            self.session.flush()
            assert User.query.count() == 1
        event.set()
        return 'ok'

    def test_thread_local_sessions(self):
        with self.session:
            event = threading.Event()
            thread = threading.Thread(target=self._thread_is_not_in_session, args=(event,))
            thread.daemon = True
            thread.start()
            thread.join()

            assert event.is_set()

    def test_nested_rollback(self):
        with pytest.raises(ValueError):
            with self.session:
                User(name='bob').save()
                with self.session:
                    User(name='fred').save()
                    self.session.flush()
                    raise ValueError

        assert not self.session._registry()._depth

    def test_explicit_rollback(self):
        with self.session:
            User(name='bob').save()
            self.session.rollback()

        with self.session:
            assert User.query.filter_by(name='bob').count() == 0

    def test_get_or_create(self):
        with self.session:
            a, a_created = User.get_or_create(name='bob')
            assert a_created

        with self.session:
            b, b_created = User.get_or_create(name='bob')
            assert not b_created

        assert a.id == b.id
