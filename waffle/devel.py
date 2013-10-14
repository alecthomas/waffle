import gevent
from injector import Module, MappingKey, inject, singleton, provides
from gevent.backdoor import BackdoorServer

from waffle.flags import Flag


DebugConsoleContext = MappingKey('DebugConsoleContext')


class DevelModule(Module):
    """Configuration useful for development.

    - Exports a BackdoorServer REPL on --console_port: injector.get(BackdoorServer).start()
    - The locals of the REPL can be contributed to by providing DebugConsoleContext.
    """

    console_port = Flag('--console_port', help='Port for debugging console.', metavar='PORT', default=8001, type=int)

    def configure(self, binder):
        binder.multibind(DebugConsoleContext, to={'injector': binder.injector})

    @singleton
    @provides(BackdoorServer)
    @inject(debug_console_context=DebugConsoleContext)
    def provide_backdoor_server(self, debug_console_context):
        backdoor = BackdoorServer(('127.0.0.1', self.console_port), debug_console_context)
        return gevent.Greenlet(backdoor.serve_forever)
