from injector import Module

from waffle.web.db import DatabaseSessionModule
from waffle.web.clastic import WebModule
from waffle.web.csrf import CsrfModule
from waffle.web.template import TemplateModule


class WebModules(Module):
    def configure(self, binder):
        binder.install(WebModule)
        binder.install(DatabaseSessionModule)
        binder.install(TemplateModule)
        binder.install(CsrfModule)
