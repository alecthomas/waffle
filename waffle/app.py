from functools import wraps

from injector import Injector

from waffle.flags import FlagsModule, parser, dispatch, add_commands, set_default_command, expects_obj


"""Running the app.

There are two primary options:

1. Traditional single entry point:

    from waffle.app import main

    @main
    def main(injector):
        pass

2. Multiple command entry points:

    from waffle.app import command, run

    @command
    def start(injector):
        pass

    @command
    def stop(injector):
        pass

    run()
"""


def _create_injector(f):
    @wraps(f)
    def wrapper(args):
        modules = [FlagsModule(args)] + getattr(f, '__injector_modules__', [])
        injector = Injector(modules)
        return f(injector)
    return wrapper


def run(**defaults):
    """Run the app, optionally setting some default command-line arguments."""
    parser.set_defaults(**defaults)
    dispatch(parser)


def modules(*modules):
    """A decorator that specifies Injector modules to use when bootstrapping the application.

    Must be provided *after* @command or @main."""
    def wrapper(f):
        f.__injector_modules__ = list(modules)
        return f
    return wrapper


def command(f):
    """A decorator to add a function as a command."""
    f = expects_obj(_create_injector(f))
    add_commands(parser, [f])
    return f


def main(_f=None, **defaults):
    """A decorator that marks and runs the main entry point.

    Basic usage:

        @main
        def main(injector):
            pass

    Optionally provide defaults for global flags:

        @main(database_uri='sqlite:///t.db')
        def main(injector):
            pass
    """
    def wrapper(f):
        f = expects_obj(_create_injector(f))
        set_default_command(parser, f)
        run(**defaults)

    if _f is not None:
        wrapper(_f)
        return
    else:
        return wrapper
