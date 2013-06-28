from injector import Module

from waffle.db import DatabaseModule
from waffle.log import LoggingModule


class AppModules(Module):
    def configure(self, binder):
        binder.install(DatabaseModule)
        binder.install(LoggingModule)
