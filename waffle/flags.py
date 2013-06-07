from argh import *  # Re-export everything from argh
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


parser = ArghParser(fromfile_prefix_chars='@')

# Add a new flag
flag = parser.add_argument
flag('--debug', help='Enable debug mode.', default=False, action='store_true')


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
        super(FlagsModule, self).__init__()
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
                binder.bind(Flag(option.dest), to=lambda v=value: v)
