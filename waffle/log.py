import logging

from injector import Module, Key, Binder, provides, inject
from logging import Formatter
try:
    from colorlog import ColoredFormatter
except ImportError:
    ColoredFormatter = None

from waffle.flags import Flag, FlagKey, AppStartup


LogLevel = Key('LogLevel')


LOG_LEVELS = ['finest', 'finer', 'fine', 'debug', 'info', 'warning', 'error', 'critical']


def _configure_logging():
    """Add fine/finer/finest logging."""
    logging.FINE = 7
    logging.FINER = 5
    logging.FINEST = 1

    logging.addLevelName(logging.FINE, 'FINE')
    logging.addLevelName(logging.FINER, 'FINER')
    logging.addLevelName(logging.FINEST, 'FINEST')

    logging.Logger.fine = lambda self, *args, **kwargs: self.log(logging.FINE, *args, **kwargs)
    logging.Logger.finer = lambda self, *args, **kwargs: self.log(logging.FINER, *args, **kwargs)
    logging.Logger.finest = lambda self, *args, **kwargs: self.log(logging.FINEST, *args, **kwargs)

    root = logging.getLogger()
    logging.fine = root.fine
    logging.finer = root.finer
    logging.finest = root.finest


_configure_logging()


class LoggingModule(Module):
    """Configure some default logging.

    - Requires the FlagsModule.
    - Will use colorlog if available.
    - Binds LogLevel to the global log level.
    """

    log_to_stdout = Flag('--log_to_stdout', action='store_true', help='Log to stdout.')
    log_format = Flag('--log_format', help='Python logging format.', default='%(name)30s.%(levelname)-7s %(message)s', metavar='FORMAT')
    log_level = Flag('--log_level', help='Minimum log level.', default='warning', choices=LOG_LEVELS, metavar='LEVEL')
    logger_levels = Flag('-L', '--logger_levels', help='Set a set of logger levels.', metavar='LOGGER=LEVEL ...', action='append', default=[], type=str)

    @provides(AppStartup)
    def provide_logging_configuration(self):
        return [self.configure_logging]

    @inject(debug=FlagKey('debug'), binder=Binder)
    def configure_logging(self, debug, binder):
        if debug:
            level = logging.FINEST
        else:
            level = getattr(logging, self.log_level.upper())

        root = logging.getLogger()

        # Completely reset logging: remove all existing handlers and filters
        map(root.removeHandler, root.handlers[:])
        map(root.removeFilter, root.filters[:])

        if self.log_to_stdout and ColoredFormatter:
            formatter = ColoredFormatter(
                '%(log_color)s' + self.log_format,
                datefmt=None,
                reset=True,
                log_colors={
                    'FINEST':   'bold_black',
                    'FINER':    'bold_black',
                    'FINE':     'purple',
                    'DEBUG':    'cyan',
                    'INFO':     'green',
                    'WARNING':  'yellow',
                    'ERROR':    'red',
                    'CRITICAL': 'red',
                }
            )
        else:
            formatter = Formatter(self.log_format)

        stdout = logging.StreamHandler()
        stdout.setLevel(level if self.log_to_stdout else logging.WARNING)
        stdout.setFormatter(formatter)

        root.addHandler(stdout)
        root.setLevel(level)

        for levels in self.logger_levels:
            name, level = levels.split('=')
            if level not in LOG_LEVELS:
                raise RuntimeError('Invalid log level ' + level)
            logging.getLogger(name).setLevel(getattr(logging, level.upper()))

        binder.bind(LogLevel, to=level)
