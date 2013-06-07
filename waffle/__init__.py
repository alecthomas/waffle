"""Application framework for Wharf.

Flask + Injector + SQLAlchemy + Jinja2

    from ape import main

    @main
    def main():
        print 'my app'
"""

from waffle.app import main, modules, run, command
