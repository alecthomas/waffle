import logging

from injector import Module, Key, inject
from logging import Formatter
try:
    from colorlog import ColoredFormatter
except ImportError:
    ColoredFormatter = None

from waffle.flags import Flag, flag


LogLevel = Key('LogLevel')


flag('--log_to_stdout', action='store_true', help='Log to stdout.')
flag('--log_format', help='Python logging format [%(default)s].', default='%(levelname)-8s %(message)s', metavar='FORMAT')


class LoggingModule(Module):
    """Configure some default logging.

    - Requires the FlagsModule.
    - Will use colorlog if available.
    - Binds LogLevel to the global log level.
    """
    @inject(debug=Flag('debug'), log_to_stdout=Flag('log_to_stdout'), log_format=Flag('log_format'))
    def configure(self, binder, debug, log_to_stdout, log_format):
        level = logging.DEBUG if debug else logging.INFO

        root = logging.getLogger()

        # Completely reset logging: remove all existing handlers and filters
        map(root.removeHandler, root.handlers[:])
        map(root.removeFilter, root.filters[:])

        if log_to_stdout and ColoredFormatter:
            formatter = ColoredFormatter(
                '%(log_color)s' + log_format,
                datefmt=None,
                reset=True,
                log_colors={
                    'DEBUG':    'cyan',
                    'INFO':     'green',
                    'WARNING':  'yellow',
                    'ERROR':    'red',
                    'CRITICAL': 'red',
                }
            )
        else:
            formatter = Formatter(log_format)

        stdout = logging.StreamHandler()
        stdout.setLevel(level if log_to_stdout else logging.WARNING)
        stdout.setFormatter(formatter)

        root.addHandler(stdout)

        root.setLevel(level)

        binder.bind(LogLevel, to=level)
