from argparse import HelpFormatter, SUPPRESS, OPTIONAL, ZERO_OR_MORE
from argh import ArghParser, arg, dispatch, expects_obj, set_default_command, dispatch, add_commands
from injector import Module, Key, singleton


"""A configuration system backed by flags and files.

- Basically a thin wrapper around argh.
- Provides a "flag" function that adds extra global flags.
- Provides a global parser which any package can add arguments to (via the "flag" function).
- Binds parsed flags (as Flags) and individual flags (as Flag('flag')) to the
  injector.
"""


# Parsed command line arguments can be injected with this key.
Flags = Key('Flags')


class ArgumentDefaultsHelpFormatter(HelpFormatter):
    def _get_help_string(self, action):
        help = action.help
        if '%(default)' not in action.help:
            if action.default is not SUPPRESS and action.default not in (True, False):
                defaulting_nargs = [OPTIONAL, ZERO_OR_MORE]
                if action.option_strings or action.nargs in defaulting_nargs:
                    if help.endswith('.'):
                        help = help[:-1]
                    help += ' [%(default)s].'
        return help


parser = ArghParser(fromfile_prefix_chars='@', formatter_class=ArgumentDefaultsHelpFormatter)


_flags = []


def flag(*args, **kwargs):
    """Register a global or command-specific flag.

    If used as a function call at the global level, will register a global flag.

        flag('--debug', help='Enable debug.', action='store_true')

    If used as a decorator on a @command, will add a command-specific flag:

        @flag('--root', help='Root directory.')
    """
    _flags.append((args, kwargs))

    def apply(f):
        args, kwargs = _flags.pop()
        return arg(*args, **kwargs)(f)

    return apply


flag('--debug', help='Enable debug mode.', action='store_true')


_flag_keys = {}


def _flag_name(name):
    return 'Flag' + name.title().replace('_', '')


def Flag(name):
    """An injector binding key for an individual flag."""
    try:
        return _flag_keys[name]
    except KeyError:
        key = _flag_keys[name] = Key(_flag_name(name))
        return key


class FlagsModule(Module):
    """Bind parsed flags to the injector.

    Note that this will only bind global flags.
    """
    def __init__(self, args):
        self.args = args

    def configure(self, binder):
        binder.bind(Flags, to=self.args, scope=singleton)
        # Bind individual flags.

        #  FIXME: Unfortunately, argh does not set defaults on any options
        # created through the @arg decorator. This means that there is no
        # obvious way to acquire the default value of one of these options,
        # and they will be None by default.
        for option in parser._actions:
            if option.dest not in ('help', '==SUPPRESS=='):
                value = getattr(self.args, option.dest, option.default)
                binder.bind(Flag(option.dest), to=lambda v=value: v, scope=singleton)


def _apply_flags():
    while _flags:
        args, kwargs = _flags.pop(0)
        parser.add_argument(*args, **kwargs)


def set_flag_defaults(**defaults):
    _apply_flags()
    parser.set_defaults(**defaults)
