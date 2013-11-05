from __future__ import absolute_import

from injector import Module, Injector, inject, singleton, provides
from jinja2 import Environment
from clastic import Response, Request

from waffle.template import TemplateContext
from waffle.web.clastic import RenderFactory, SessionCookie


"""Template support for the Waffle web layer.

Provides a Clastic renderer, and middleware that configures the Jinja context.
"""


class Jinja2RenderFactory(object):
    def __init__(self, env, injector):
        self._env = env
        self._injector = injector

    def __call__(self, template_filename):
        def render(context):
            template = self._env.get_template(template_filename)
            merged_context = dict(self._injector.get(TemplateContext), **context)
            content = template.render(**merged_context)
            return Response(content, status=200, mimetype='text/html')

        return render


class WebTemplateModule(Module):
    """Add support for Jinja2 templates to Clastic."""

    @provides(RenderFactory, scope=singleton)
    @inject(environment=Environment, injector=Injector)
    def provide_render_factory(self, environment, injector):
        return Jinja2RenderFactory(environment, injector)

    @provides(TemplateContext)
    @inject(session=SessionCookie, request=Request)
    def provide_template_context(self, session, request):
        return {'session': session, 'request': request}
