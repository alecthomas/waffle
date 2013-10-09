from __future__ import absolute_import

import logging
from uuid import uuid4

from injector import Module, Binder, provides, inject
from clastic import Middleware
from werkzeug.exceptions import BadRequest

from waffle.flags import Flag
from waffle.web.clastic import Middlewares, SessionCookie, request
from waffle.web.template import TemplateContext


logger = logging.getLogger(__name__)


class CsrfMiddleware(Middleware):
    def __init__(self, binder):
        self._binder = binder

    def request(self, next, request, session, _route):
        if request.method == "POST" and not hasattr(_route.endpoint, '__csrf_exempt__'):
            csrf_token = session.pop('_csrf_token', None)
            if not csrf_token or csrf_token != request.form.get('_csrf_token'):
                raise BadRequest('invalid CSRF token')

        return next()


def csrf_exempt(f):
    """Mark a route as being exempt from CSRF."""
    f.__csrf_exempt__ = True
    return f


class CsrfModule(Module):
    """Provide CSRF support to the template module."""

    @provides(Middlewares)
    @inject(debug=Flag('debug'), binder=Binder)
    def provides_sea_surf_extension(self, debug, binder):
        return [CsrfMiddleware(binder)]

    @provides(TemplateContext, scope=request)
    @inject(session=SessionCookie)
    def provide_template_csrf_token(self, session):
        def generate_csrf_token():
            if '_csrf_token' not in session:
                session['_csrf_token'] = str(uuid4())
            return session['_csrf_token']

        return {'csrf_token': generate_csrf_token}
