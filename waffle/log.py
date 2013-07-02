import logging

from injector import Module, Key, inject
from logging import Formatter
try:
    from colorlog import ColoredFormatter
except ImportError:
    ColoredFormatter = None

from waffle.flags import Flags, flag


LogLevel = Key('LogLevel')


flag('--log_to_stdout', action='store_true', help='Log to stdout.')
flag('--log_format', help='Python logging format.', default='%(levelname)-8s %(message)s', metavar='FORMAT')
flag('--log_level', help='Minimum log level.', default='warning', choices=['debug', 'info', 'warning', 'error', 'critical'], metavar='LEVEL')


class LoggingModule(Module):
    """Configure some default logging.

    - Requires the FlagsModule.
    - Will use colorlog if available.
    - Binds LogLevel to the global log level.
    """
    @inject(flags=Flags)
    def configure(self, binder, flags):
        if flags.debug:
            level = logging.DEBUG
        else:
            level = getattr(logging, flags.log_level.upper())

        root = logging.getLogger()

        # Completely reset logging: remove all existing handlers and filters
        map(root.removeHandler, root.handlers[:])
        map(root.removeFilter, root.filters[:])

        if flags.log_to_stdout and ColoredFormatter:
            formatter = ColoredFormatter(
                '%(log_color)s' + flags.log_format,
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
            formatter = Formatter(flags.log_format)

        stdout = logging.StreamHandler()
        stdout.setLevel(level if flags.log_to_stdout else logging.WARNING)
        stdout.setFormatter(formatter)

        root.addHandler(stdout)
        root.setLevel(level)

        binder.bind(LogLevel, to=level)
