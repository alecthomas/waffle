from waffle.flags import parser, dispatch, add_commands, set_default_command, expects_obj


"""Running the app.

There are two primary options:

1. Traditional single entry point:

    from waffle.app import main

    @main
    def main(args):
        pass

2. Multiple command entry points:

    from waffle.app import command, run

    @command
    def start(args):
        pass

    @command
    def stop(args):
        pass

    run()
"""


def run(**defaults):
    """Run the app, optionally setting some default command-line arguments."""
    parser.set_defaults(**defaults)
    dispatch(parser)


def command(f):
    """A decorator to add a function as a command."""
    f = expects_obj(f)
    add_commands(parser, [f])
    return f


def main(_f=None, **defaults):
    """A decorator that marks and runs the main entry point.

    Basic usage:

        @main
        def main():
            pass

    Optionally provide defaults for global flags:

        @main(database_uri='sqlite:///t.db')
        def main():
            pass
    """
    def wrapper(f):
        parser.set_defaults(**defaults)
        f = expects_obj(f)
        set_default_command(parser, f)
        run()
    if _f is not None:
        wrapper(_f)
        return
    else:
        return wrapper
