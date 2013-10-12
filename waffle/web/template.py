from __future__ import absolute_import

import codecs
import os

from injector import Module, MappingKey, Binder, Injector, inject, singleton, provides
from jinja2 import Environment, BaseLoader, TemplateNotFound, StrictUndefined
from clastic import Middleware, Response

from waffle.flags import Flag, flag
from waffle.web.clastic import RenderFactory, Middlewares, RequestScope


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


flag('--template_root', metavar='DIR', help='Root directory for HTML templates.')


_filters = {}


def template_filter(name):
    """Register a template filter."""
    def apply(f):
        _filters[name] = f
        return f
    return apply


@singleton
class Loader(BaseLoader):
    """Template loader."""
    @inject(template_root=Flag('template_root'))
    def __init__(self, template_root):
        assert template_root, 'template_root must be provided'
        self._template_root = template_root

    def get_source(self, environment, template):
        path = os.path.join(self._template_root, template)
        if not os.path.exists(path):
            raise TemplateNotFound(template)
        mtime = os.path.getmtime(path)
        with codecs.open(path, encoding='utf-8') as fd:
            return fd.read(), path, lambda: mtime == os.path.getmtime(path)


class Jinja2RenderFactory(object):
    def __init__(self, env, injector):
        self._env = env
        self._injector = injector

    def __call__(self, template_filename):
        template = self._env.get_template(template_filename)

        def render(context):
            merged_context = dict(self._injector.get(TemplateContext), **context)
            content = template.render(**merged_context)
            return Response(content, status=200, mimetype='text/html')

        return render


class UrlFor(object):
    def __init__(self, url_adapter):
        self._url_adapter = url_adapter

    def __call__(self, endpoint, **values):
        force_external = values.pop('force_external', False)
        return self._url_adapter.build(endpoint, values, force_external=force_external)


class TemplateMiddleware(Middleware):
    def __init__(self, binder):
        self._binder = binder

    def request(self, next, request, session):
        self._binder.bind(TemplateContext, to={
            'session': session,
            'request': request,
            # 'url_for': url_for,
            # 'static': lambda filename: url_for('static', filename=filename),
            }, scope=RequestScope)
        return next()


class TemplateModule(Module):
    """Add support for Jinja2 templates.

    Provides compiled templates via Template(template), and the Environment
    itself. The default context for a template can be extended by multibinding
    TemplateContext.
    """
    @inject(debug=Flag('debug'))
    def configure(self, binder, debug):
        binder.multibind(TemplateGlobals, to={}, scope=singleton)
        binder.multibind(TemplateFilters, to={}, scope=singleton)
        binder.multibind(TemplateContext, to={'debug': debug}, scope=RequestScope)

    @provides(Environment, scope=singleton)
    @inject(loader=Loader, debug=Flag('debug'), filters=TemplateFilters, globals=TemplateGlobals)
    def provides_template_environment(self, loader, debug, filters, globals=globals):
        env = Environment(loader=loader, autoescape=True, auto_reload=debug, undefined=StrictUndefined)
        env.filters.update(_filters)
        env.filters.update(filters)
        env.globals.update(globals)
        return env

    @provides(RenderFactory, scope=singleton)
    @inject(environment=Environment, injector=Injector)
    def provide_render_factory(self, environment, injector):
        return Jinja2RenderFactory(environment, injector)

    @provides(Middlewares, scope=singleton)
    @inject(binder=Binder)
    def provide_template_middleware(self, binder):
        return [TemplateMiddleware(binder)]
