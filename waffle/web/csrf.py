from __future__ import absolute_import

import logging

from injector import Module, provides, inject
from flask.ext.seasurf import SeaSurf

from waffle.web.flask import FlaskExtensions, decorator
from waffle.flags import Flag


logger = logging.getLogger(__name__)


csrf_exempt = decorator(SeaSurf.exempt)


def init_dummy_csrf(app):
    app.jinja_env.globals['csrf_token'] = lambda: ''


class CsrfModule(Module):
    @provides(FlaskExtensions)
    @inject(debug=Flag('debug'))
    def provides_sea_surf_extension(self, debug):
        if debug:
            logger.warning('CSRF protection disabled in debug mode')
            return [init_dummy_csrf]
        else:
            csrf = SeaSurf()
            return [csrf]
