from __future__ import absolute_import

import codecs
import os

from injector import Module, MappingKey, inject, singleton, provides
from jinja2 import Environment, BaseLoader, TemplateNotFound, StrictUndefined

from waffle.flags import Flag, FlagKey


"""Jinja2 based templating system for Waffle.

The render context for templates can be extended by Injector modules with:

    binder.multibind(TemplateContext, to={
        'debug': debug,
    })

"""


# A binding key for contributors to the template context. See
# :class:`TemplateModule` for an example of how to extend the context.
TemplateContext = MappingKey('TemplateContext')
# Jinja2 template globals.
TemplateGlobals = MappingKey('TemplateGlobals')
# A binding key for contributing filters to templates.
TemplateFilters = MappingKey('TemplateFilters')


_filters = {}
_functions = {}


def template_filter(name):
    """Register a template filter."""
    def apply(f):
        _filters[name] = f
        return f
    return apply


def template_function(name):
    """Register a global function."""
    def apply(f):
        _functions[name] = f
        return f
    return apply


@singleton
class Loader(BaseLoader):
    """Template loader."""

    @inject(template_root=FlagKey('template_root'))
    def __init__(self, template_root):
        self._template_root = template_root

    def get_source(self, environment, template):
        path = os.path.join(self._template_root, template)
        if not os.path.exists(path):
            raise TemplateNotFound(template)
        mtime = os.path.getmtime(path)
        with codecs.open(path, encoding='utf-8') as fd:
            return fd.read(), path, lambda: mtime == os.path.getmtime(path)


class TemplateModule(Module):
    """Add support for Jinja2 templates.

    Provides compiled templates via Template(template), and the Environment
    itself. The default context for a template can be extended by multibinding
    TemplateContext.
    """

    template_root = Flag('--template_root', metavar='DIR', help='Root directory for HTML templates.', required=True)

    def configure(self, binder):
        binder.multibind(TemplateGlobals, to={}, scope=singleton)
        binder.multibind(TemplateFilters, to={}, scope=singleton)
        binder.multibind(TemplateContext, to={})

    @provides(TemplateGlobals)
    @inject(debug=FlagKey('debug'))
    def provide_template_globals(self, debug):
        return {'debug': debug}

    @provides(Environment, scope=singleton)
    @inject(loader=Loader, debug=FlagKey('debug'), filters=TemplateFilters, globals=TemplateGlobals)
    def provides_template_environment(self, loader, debug, filters, globals=globals):
        env = Environment(loader=loader, autoescape=True, auto_reload=debug, undefined=StrictUndefined)
        env.filters.update(_filters)
        env.filters.update(filters)
        env.globals.update(_functions)
        env.globals.update(globals)
        return env
