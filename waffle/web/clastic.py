from __future__ import absolute_import

from injector import Injector, Module, Scope, ScopeDecorator, InstanceProvider, \
    Key, Binder, SequenceKey, MappingKey, provides, inject, singleton
from clastic import Application, Middleware as WebMiddleware, Request, render_basic
from clastic.middleware.session import CookieSessionMiddleware, JSONCookie
from werkzeug.local import Local, LocalManager

from waffle.flags import Flag, Flags


Routes = SequenceKey('Routes')
Middlewares = SequenceKey('Middlewares')
Resources = MappingKey('Resources')
ErrorHandlers = MappingKey('ErrorHandlers')
RenderFactory = Key('RenderFactory')
SessionCookie = JSONCookie


_routes = []


class RoutesModule(Module):
    def __init__(self, routes):
        self._routes = routes or []

    def configure(self, binder):
        binder.multibind(Routes, to=self._routes)


def routes(*routes):
    """A decorator that adds routes to the injector."""

    routes = [(f.__route__[0], f, f.__route__[1]) for f in routes]
    modules = [RoutesModule(routes)]

    def wrapper(f):
        f.__injector_modules__ = getattr(f, '__injector_modules__', []) + modules
        return f

    return wrapper


def route(path, renderer=render_basic):
    def apply(f):
        f.__route__ = (path, renderer)
        _routes.append((path, f, renderer))
        return f

    return apply


class RequestScope(Scope):
    """A scope whose object lifetime is tied to a request.

    @request
    class Session(object):
        pass
    """

    def reset(self):
        self._local_manager.cleanup()
        self._locals.scope = {}

    def configure(self):
        self._locals = Local()
        self._local_manager = LocalManager([self._locals])
        self.reset()

    def get(self, key, provider):
        try:
            return self._locals.scope[key]
        except KeyError:
            provider = InstanceProvider(provider.get())
            self._locals.scope[key] = provider
            return provider


request = ScopeDecorator(RequestScope)


class RequestScopeMiddleware(WebMiddleware):
    @inject(scope=RequestScope, binder=Binder)
    def __init__(self, scope, binder):
        self._scope = scope
        self._binder = binder

    def request(self, next, request, session):
        self._scope.reset()
        self._binder.bind(SessionCookie, to=session, scope=RequestScope)
        self._binder.bind(Request, to=request, scope=RequestScope)
        try:
            return next()
        finally:
            self._scope.reset()


@singleton
class WebApplication(Application):
    """An injector aware subclass of clastic.Application."""

    @inject(middlewares=Middlewares, routes=Routes, resources=Resources,
            error_handlers=ErrorHandlers, injector=Injector,
            render_factory=RenderFactory)
    def __init__(self, middlewares, routes, resources, error_handlers, injector,
                 render_factory, **kwargs):
        # Make routes injectable.
        routes = [(p, (injector.wrap_function(f) if hasattr(f, '__bindings__') else f), r)
                  for p, f, r in routes]
        super(WebApplication, self).__init__(
            routes=routes,
            resources=resources,
            middlewares=middlewares,
            error_handlers=error_handlers,
            render_factory=render_factory,
            **kwargs
            )

    @inject(flags=Flags)
    def serve(self, flags, **kwargs):
        args = dict(address=flags.bind_address, port=flags.bind_port, use_reloader=flags.debug, **kwargs)
        return super(WebApplication, self).serve(**args)


class WebModule(Module):
    static_root = Flag('--static_root', help='Path to web server static resources.', metavar='PATH')
    bind_address = Flag('--bind_address', help='Address to bind HTTP server to.', metavar='IP', default='127.0.0.1')
    bind_port = Flag('--bind_port', help='Port to bind HTTP server to.', metavar='PORT', type=int, default='8080')

    def configure(self, binder):
        binder.bind_scope(RequestScope)
        binder.multibind(Routes, to=[], scope=singleton)
        binder.multibind(Resources, to={}, scope=singleton)
        binder.multibind(ErrorHandlers, to={}, scope=singleton)
        binder.bind(RenderFactory, to=None, scope=singleton)
        binder.bind(RequestScopeMiddleware)
        binder.multibind(Middlewares, to=[
            CookieSessionMiddleware(cookie_name='waffle_session'),
            binder.injector.get(RequestScopeMiddleware),
        ], scope=singleton)
        binder.multibind(Routes, to=_routes, scope=singleton)
