import inspect

import flask
from flask import Flask, Config, Request
from flask.views import View
from werkzeug.local import Local, LocalManager
from injector import Module, Injector, SequenceKey, MappingKey, ScopeDecorator, Scope, InstanceProvider, provides, inject

from waffle.flags import Flag, flag


__all__ = ['route', 'Controllers', 'RequestTeardown', 'FlaskModule']


Controllers = SequenceKey('Controllers')
RequestTeardown = SequenceKey('RequestTeardown')
ErrorHandlers = MappingKey('ErrorHandlers')


flag('--static_root', help='Path to web server static resources [%(default)s].', metavar='PATH')


class ControllersModule(Module):
    def __init__(self, controllers):
        self._controllers = controllers or []

    def configure(self, binder):
        binder.multibind(Controllers, to=self._controllers)


def controllers(*controllers):
    """A decorator that adds Flask controllers to the injector."""

    modules = [ControllersModule(controllers)]

    def wrapper(f):
        f.__injector_modules__ = getattr(f, '__injector_modules__', []) + modules
        return f

    return wrapper


class InjectorView(View):
    """A Flask View that applies argument injection to a decorated function."""

    def __init__(self, handler, injector, request_scope, handler_class=None):
        self._handler = handler
        self._injector = injector
        self._handler_class = handler_class
        self._request_scope = request_scope

    def dispatch_request(self, **kwargs):
        # Not @injected
        self._request_scope.reset()
        handler = self._handler
        if self._handler_class:
            instance = self._injector.get(self._handler_class)
            handler = self._handler.__get__(instance, self._handler_class)
        if not hasattr(handler, '__bindings__'):
            return handler(**kwargs)
        bindings = self._injector.args_to_inject(
            function=handler,
            bindings=handler.__bindings__,
            owner_key=handler.__module__,
            )
        try:
            return self._handler(**dict(bindings, **kwargs))
        finally:
            self._request_scope.reset()


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


def route(*args, **kwargs):
    """Decorate a function as a view endpoint."""
    def _wrap(f):
        f.__view__ = (args, kwargs)
        return f
    return _wrap


class decorator(object):
    """Convert a Flask extension decorator to a Flask-Injector decorator.

    Normally, Flask extension decorators are used like so:

        app = Flask(__name__)
        cache = Cache(app)

        @cache.cached(timeout=30)
        def route():
            return 'Hello world'

    As this requires global state (Flask app and Cache object), this class
    exists to inject the provided class instance on-demand. eg.

        cached = decorator(Cache.cached)

        ...

        @cached(timeout=30)
        def route():
            return 'Hello world'

    The Cache instance must be provided in an Injector module:

        class CacheModule(Module):
            @provides(Cache)
            @singleton
            @inject(app=Flask)
            def provides_cache(self, app):
                return Cache(app)

        app = Flask(__name__)
        builder = Builder([view], [CacheModule()], config={
            # Cache configuration keys here
            })
        builder.init_app(app)
        app.run()
    """

    class State(object):
        def __init__(self, f):
            self.f = f
            self.args = None
            self.kwargs = None

        def apply(self, injector, view):
            cls = self.f.im_class
            instance = injector.get(cls)
            decorator = self.f.__get__(instance, cls)
            return decorator(*self.args, **self.kwargs)(view)

    # Mapping from extension type to extension decorator
    ext_registry = {}
    state_registry = []

    def __init__(self, f):
        # cached = decorator(Cache.cached)
        decorator.ext_registry[f.im_class] = f
        self.state = decorator.State(f)
        decorator.state_registry.append(self.state)

    def __call__(self, *args, **kwargs):
        # @cached(timeout=30)
        self.state.args = args
        self.state.kwargs = kwargs

        def wrap(f):
            if not hasattr(f, '__decorators__'):
                f.__decorators__ = []
            f.__decorators__.append(self.state)
            return f

        return wrap


class FlaskModule(Module):
    """Provides a dependency-injected Flask application.

    - Controllers should be provided by other modules via the `Controllers`
      key (or more conveniently by the controllers() main decorator).
    - Request teardown callbacks can be registered by providing the
      `RequestTeardown` value.
    - Error handlers can be registered by providing the `ErrorHandlers`
      callback.
    """

    def configure(self, binder):
        binder.bind_scope(RequestScope)
        binder.bind(Request, to=lambda: flask.request)
        binder.multibind(Controllers, to=[])
        binder.multibind(RequestTeardown, to=[])
        binder.multibind(ErrorHandlers, to={})

    @provides(Config)
    @inject(app=Flask)
    def provides_flask_config(self, app):
        return app.config

    @provides(Flask)
    @inject(static_root=Flag('static_root'), debug=Flag('debug'), injector=Injector,
            controllers=Controllers, teardown=RequestTeardown, error_handlers=ErrorHandlers)
    def provide_flask(self, static_root, debug, injector, controllers, teardown, error_handlers):
        assert static_root, '--static_root not set, set a default in main() or run()'
        app = Flask('app', static_folder=static_root)
        app.debug = debug

        # Request teardown callbacks
        for callback in teardown:
            app.teardown_request(lambda e=None, c=callback: c())

        # Error handlers
        for error, handler in error_handlers.iteritems():
            app.errorhandler(error)(lambda e=None, c=handler: c())

        self._configure_controllers(injector, app, controllers)
        return app

    def _configure_controllers(self, injector, app, controllers):
        request_scope = injector.get(RequestScope)
        # Generate controllers
        for controller in controllers:
            if inspect.isclass(controller):
                self._reflect_controllers_from_class(controller, injector, app)
            else:
                assert hasattr(controller, '__view__')
                iview = InjectorView.as_view(controller.__name__, handler=controller, injector=injector, request_scope=request_scope)
                iview = self._install_route(injector, app, controller, iview, *controller.__view__)

    def _reflect_controllers_from_class(self, cls, injector, app):
        class_view = getattr(cls, '__view__', None)
        assert class_view is None or len(class_view[0]) == 1, \
            'Path prefix is the only non-keyword argument allowed on class @controller for ' + str(cls)
        prefix = class_view[0][0] if class_view is not None else ''
        class_kwargs = class_view[1]
        for name, method in inspect.getmembers(cls, lambda m: inspect.ismethod(m) and hasattr(m, '__view__')):
            args, kwargs = method.__view__
            args = (prefix + args[0],) + args[1:]
            kwargs = dict(class_kwargs, **kwargs)
            iview = InjectorView.as_view(name, handler=method, injector=injector, handler_class=cls)
            self._install_route(injector, app, method, iview, args, kwargs)

    def _install_route(self, injector, app, controller, iview, args, kwargs):
        if hasattr(controller, '__decorators__'):
            for state in controller.__decorators__:
                iview = state.apply(injector, iview)
        app.add_url_rule(*args, view_func=iview, **kwargs)
