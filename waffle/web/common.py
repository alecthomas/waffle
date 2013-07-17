from injector import Module

from waffle.web.db import DatabaseSessionModule
from waffle.web.flask import FlaskModule
from waffle.web.template import TemplateModule
from waffle.web.csrf import CsrfModule


class WebModules(Module):
    def configure(self, binder):
        binder.install(FlaskModule)
        binder.install(DatabaseSessionModule)
        binder.install(TemplateModule)
        binder.install(CsrfModule)
