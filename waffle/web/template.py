import codecs
import os

from injector import Module, ParameterizedBuilder, MappingKey, inject, singleton, provides
from jinja2 import Environment, BaseLoader, TemplateNotFound

from waffle.flags import Flag, flag


"""Jinja2 based templating system for Waffle.

This system does not rely on Flask.

- Jinja2 templates are used server side and nunjucks templates are used client
  side.
- The render context for templates can be extended by Injector modules with:

    binder.multibind(TemplateContext, to={
        'debug': debug,
    })

"""


# A binding key for contributors to the template context. See
# :class:`TemplateModule` for an example of how to extend the context.
TemplateContext = MappingKey('TemplateContext')


flag('--template_root', metavar='DIR',
    help='Root directory for HTML templates.')


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


class Renderer(object):
    @inject(environment=Environment)
    def __init__(self, filename, environment):
        self._template = environment.get_template(filename)

    @inject(template_context=TemplateContext)
    def __call__(self, context={}, template_context={}):
        context = dict(template_context, **context)
        return self._template.render(**context)


def Template(filename):
    """Inject a compiled template."""
    return singleton(ParameterizedBuilder(Renderer, filename=filename))


class TemplateModule(Module):
    """Add support for Jinja2 templates.

    Provides compiled templates via Template(template), and the Environment
    itself. The default context for a template can be extended by multibinding
    TemplateContext.
    """
    @inject(debug=Flag('debug'))
    def configure(self, binder, debug):
        binder.multibind(TemplateContext, to={
            'debug': debug,
        })

    @singleton
    @provides(Environment)
    @inject(loader=Loader)
    def provides_template_environment(self, loader):
        return Environment(loader=loader)
