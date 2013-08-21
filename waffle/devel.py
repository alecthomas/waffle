import gevent
from injector import Module, MappingKey, inject, singleton, provides
from gevent.backdoor import BackdoorServer

from waffle.flags import Flag, flag


flag('--console_port', help='Port for debugging console.', metavar='PORT', default=8001, type=int)


DebugConsoleContext = MappingKey('DebugConsoleContext')


class DevelModule(Module):
    """Configuration useful for development.

    - Exports a BackdoorServer REPL on --console_port: injector.get(BackdoorServer).start()
    - The locals of the REPL can be contributed to by providing DebugConsoleContext.
    """

    def configure(self, binder):
        binder.multibind(DebugConsoleContext, to={'injector': binder.injector})

    @singleton
    @provides(BackdoorServer)
    @inject(console_port=Flag('console_port'), debug_console_context=DebugConsoleContext)
    def provide_backdoor_server(self, console_port, debug_console_context):
        backdoor = BackdoorServer(('127.0.0.1', console_port), debug_console_context)
        return gevent.Greenlet(backdoor.serve_forever)
