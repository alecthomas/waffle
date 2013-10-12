"""Application framework for Wharf.

Flask + Injector + SQLAlchemy + Jinja2

    from waffle import main

    @main
    def main():
        print 'my app'
"""

from types import ModuleType
import sys

__version__ = '0.2.1'

# import mapping to objects in other modules
all_by_module = {
    'waffle.common':        ['AppModules'],
    'waffle.app':           ['run', 'modules', 'command', 'main', 'create_injector_from_flags'],
    'waffle.db':            ['DatabaseSession', 'Model', 'DatabaseModule',
                             'DatabaseEngine', 'transaction', 'session_from'],
    'waffle.flags':         ['Flags', 'flag', 'parser', 'Flag',
                             'FlagsModule', 'set_flag_defaults'],
    'waffle.devel':         ['DebugConsoleContext', 'DevelModule'],
    'waffle.redis':         ['RedisModule'],
    'waffle.log':           ['LogLevel', 'LoggingModule'],
    'waffle.web.common':    ['WebModules'],
    'waffle.web.clastic':   ['RequestScope', 'WebModule', 'WebApplication', 'Request',
                             'Routes', 'Middlewares', 'Resources', 'ErrorHandlers',
                             'RenderFactory', 'SessionCookie', 'route', 'routes'],
    'waffle.web.csrf':      ['CsrfModule', 'csrf_exempt'],
    'waffle.web.db':        ['DatabaseSessionModule'],
    'waffle.web.template':  ['TemplateContext', 'TemplateGlobals', 'TemplateFilters',
                             'TemplateModule', 'template_filter'],
}

# modules that should be imported when accessed as attributes of waffle
attribute_modules = frozenset([])


object_origins = {}
for module, items in all_by_module.iteritems():
    for item in items:
        object_origins[item] = module


class module(ModuleType):
    """Automatically import objects from the modules."""

    def __getattr__(self, name):
        if name in object_origins:
            module = __import__(object_origins[name], None, None, [name])
            for extra_name in all_by_module[module.__name__]:
                setattr(self, extra_name, getattr(module, extra_name))
            return getattr(module, name)
        elif name in attribute_modules:
            __import__('waffle.' + name)
        return ModuleType.__getattribute__(self, name)

    def __dir__(self):
        """Just show what we want to show."""
        result = list(new_module.__all__)
        result.extend(('__file__', '__path__', '__doc__', '__all__',
                       '__docformat__', '__name__', '__path__',
                       '__package__', '__version__'))
        return result

# keep a reference to this module so that it's not garbage collected
old_module = sys.modules['waffle']


# setup the new module and patch it into the dict of loaded modules
new_module = sys.modules['waffle'] = module('waffle')
new_module.__dict__.update({
    '__file__':         __file__,
    '__package__':      'waffle',
    '__path__':         __path__,
    '__doc__':          __doc__,
    '__version__':      __version__,
    '__all__':          tuple(object_origins) + tuple(attribute_modules),
    '__docformat__':    'restructuredtext en'
})
