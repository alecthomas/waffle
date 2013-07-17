from __future__ import absolute_import

from injector import Module, provides
from flask.ext.seasurf import SeaSurf

from waffle.web.flask import FlaskExtensions, decorator


csrf_exempt = decorator(SeaSurf.exempt)


class CsrfModule(Module):
    @provides(FlaskExtensions)
    def provides_sea_surf_extension(self):
        csrf = SeaSurf()
        return [csrf]
