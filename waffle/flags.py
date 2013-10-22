import sys
import inspect
from functools import wraps
from itertools import chain

from argparse import ArgumentParser, HelpFormatter, SUPPRESS, OPTIONAL, ZERO_OR_MORE
from injector import Injector, Binder, Module, Key, SequenceKey, MappingKey, singleton, provides, inject


"""A configuration system backed by flags and files.

- Basically a thin wrapper around argh.
- Provides a "Flag" property for use in modules that adds global flags.
- Provides a global parser which any package can add arguments to (via the "flag" function).
- Binds parsed flags (as Flags) and individual flags (as FlagKey('flag')) to the
  injector.
- Also provides several decorators for bootstrapping an application with flags.
"""


AppStartup = SequenceKey('AppStartup')
# Parsed command line arguments can be injected with this key, or individually with FlagKey(name)
Flags = Key('Flags')
_ProvidedFlags = SequenceKey('_ProvidedFlags')
FlagDefaults = MappingKey('FlagDefaults')


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


_flag_key_cache = {}


def _flag_key_name(name):
    return 'Flag' + name.title().replace('_', '')


def FlagKey(name):
    """An injector binding key for an individual flag.

    Use this to inject individual flag values.
    """
    try:
        return _flag_key_cache[name]
    except KeyError:
        key = _flag_key_cache[name] = Key(_flag_key_name(name))
        return key


class _ProvideFlag(object):
    def __init__(self, dest, *args, **kwargs):
        self._dest = dest
        self._args = args
        self._kwargs = kwargs

    def __get__(self, instance, owner):
        if instance is None:
            return owner
        return instance.__injector__.get(FlagKey(self._dest))


def _extract_dest(args, kwargs):
    if 'dest' in kwargs:
        return kwargs['dest']
    for arg in args:
        if arg.startswith('--'):
            return arg[2:]
    for arg in args:
        if arg.startswith('-'):
            return arg[1:]
    raise ValueError('could not extract dest for flag with args %r %r' % (args, kwargs))


def Flag(*args, **kwargs):
    """Provide a flag from an Injector module.

        class MyModule(Module):
            debug = Flag('--debug', help='Enable debug')

    This flag is available as a property to that module, and via injection
    with FlagKey('debug').
    """

    dest = _extract_dest(args, kwargs)

    @provides(_ProvidedFlags)
    def provide_flag(self):
        return [(args, kwargs)]
    provide_flag.__name__ = 'provides_flag_' + dest

    @provides(FlagKey(dest), scope=singleton)
    @inject(flags=Flags)
    def provide_flag_value(self, flags):
        return getattr(flags, dest)
    provide_flag_value.__name__ = 'provides_flag_value_' + dest

    # There is a bit of magic here. We basically inject two @provide methods
    # into the calling scope. They provide the initial flag parameters, and the
    # final flag value.
    frames = inspect.stack()
    frames[1][0].f_locals[provide_flag.__name__] = provide_flag
    frames[1][0].f_locals[provide_flag_value.__name__] = provide_flag_value

    return _ProvideFlag(dest, *args, **kwargs)


class FlagsModule(Module):
    """Provide flags to an Injector."""

    debug = Flag('--debug', help='Enable debug mode.', action='store_true')

    def __init__(self, args, defaults=None):
        self.args = args
        self.defaults = defaults or {}

    @provides(ArgumentParser, scope=singleton)
    @inject(binder=Binder, flags=_ProvidedFlags)
    def provide_argh_parser(self, binder, flags):
        parser = ArgumentParser(fromfile_prefix_chars='@', formatter_class=ArgumentDefaultsHelpFormatter)
        for args, kwargs in flags:
            parser.add_argument(*args, **kwargs)
        return parser

    @provides(Flags, scope=singleton)
    @inject(parser=ArgumentParser, defaults=FlagDefaults)
    def provide_flags(self, parser, defaults):
        parser.set_defaults(**defaults)
        parser.set_defaults(**self.defaults)
        # NOTE: parser.set_defaults() does not satisfy "required" arguments,
        # so we synthesize flags in order to override them. Annoying. Bug?
        default_args = []
        for k, v in chain(defaults.iteritems(), self.defaults.iteritems()):
            if isinstance(v, bool):
                default_args.append('--%s' % k)
            else:
                default_args.append('--%s=%s' % (k, v))
        return parser.parse_args(default_args + self.args[1:])

    def configure(self, binder):
        binder.multibind(FlagDefaults, to={}, scope=singleton)
        binder.multibind(_ProvidedFlags, to=[], scope=singleton)


class FlagModule(Module):
    """A module providing a single flag."""

    def __init__(self, args, kwargs):
        self._args = args
        self._kwargs = kwargs
        self._dest = _extract_dest(args, kwargs)

    def configure(self, binder):
        binder.bind(FlagKey(self._dest), to=self.provide_flag_value, scope=singleton)

    @provides(_ProvidedFlags)
    def provide_flag(self):
        return [(self._args, self._kwargs)]

    @inject(flags=Flags)
    def provide_flag_value(self, flags):
        return getattr(flags, self._dest)


def flag(*args, **kwargs):
    """A convenience decorator for main/module that adds flags."""
    def wrap(f):
        f.__injector_modules__ = getattr(f, '__injector_modules__', []) + [FlagModule(args, kwargs)]
        return f
    return wrap


def create_injector_from_flags(args=None, modules=[], defaults=None, **kwargs):
    """Create an application Injector from command line flags.

    Calls all AppStartup hooks.
    """
    if args is None:
        args = sys.argv
    modules = [FlagsModule(args, defaults=defaults)] + modules
    injector = Injector(modules, **kwargs)
    injector.binder.multibind(AppStartup, to=[])
    for startup in injector.get(AppStartup):
        injector.call_with_injection(startup)
    return injector


def modules(*modules):
    """A decorator that specifies Injector modules to use when bootstrapping the application.

    See :func:`main` for details.
    """
    def wrapper(f):
        f.__injector_modules__ = getattr(f, '__injector_modules__', []) + list(modules)
        return f
    return wrapper


def main(_f=None, **defaults):
    """A decorator that marks and runs the main entry point.

    *MUST* be the top-most decorator.

    Basic usage:

        @main
        def main():
            pass

    Optionally provide defaults for global flags:

        @main(database_uri='sqlite:///t.db')
        @modules(MyMainModule, AppModules, WebModules)
        def main():
            pass
    """
    def wrapper(f):
        injector = create_injector_from_flags(modules=getattr(f, '__injector_modules__', []), defaults=defaults)

        @wraps(f)
        def inner():
            # Force all flags to be parsed.
            injector.get(Flags)
            return injector.call_with_injection(f)

        inner()

    if _f is not None:
        wrapper(_f)
        return
    else:
        return wrapper
