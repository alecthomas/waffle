import logging

import gevent
from injector import Module, inject, singleton
from gevent.backdoor import BackdoorServer

from waffle.flags import Flag, flag


flag('--console_port', help='Port for debugging console [%(default)s].', metavar='PORT', default=8001)


class DevelModule(Module):
    """Configuration useful for development."""

    @inject(debug=Flag('debug'))
    def configure(self, binder, debug):
        if not debug:
            logging.info('Developer tools disabled in production mode')
            return
        binder.bind(BackdoorServer, to=self.provide_backdoor_server)

    @singleton
    @inject(console_port=Flag('console_port'))
    def provide_backdoor_server(self, console_port):
        logging.warning('Starting console server on telnet://127.0.0.1:%d', console_port)
        backdoor = BackdoorServer(('127.0.0.1', console_port), locals())
        gevent.spawn(backdoor.serve_forever)
        return backdoor
