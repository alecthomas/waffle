import inspect

import flask
from flask import Flask, Config, Request
from flask.ext.injector import RequestScope, InjectorView
from injector import Module, Injector, SequenceKey, singleton, provides, inject

from waffle.flags import Flag, flag


Views = SequenceKey('Views')
RequestTeardown = SequenceKey('RequestTeardown')


flag('--static_root', help='Path to web server static resources.', metavar='PATH')


class FlaskModule(Module):
    def configure(self, binder):
        binder.bind_scope(RequestScope)
        binder.bind(Request, to=lambda: flask.request)
        binder.multibind(Views, to=[])

    @provides(Config)
    @inject(app=Flask)
    def provides_flask_config(self, app):
        return app.config

    @provides(Flask)
    @inject(static_root=Flag('static_root'), debug=Flag('debug'), injector=Injector, views=Views)
    def provide_flask(self, static_root, debug, injector, views):
        assert static_root, '--static_root not set, set a default in main() or run()'
        app = Flask('app', static_folder=static_root)
        app.debug = debug
        self._configure_views(injector, app, views)
        return app

    @singleton
    @provides(RequestTeardown)
    @inject(app=Flask)
    def provides_request_teardown(self, app):
        @app.teardown_request
        @inject(callbacks=RequestTeardown)
        def request_teardown(self, exception=None, callbacks=None):
            for callback in callbacks:
                callback()
        return []

    def _configure_views(self, injector, app, views):
        # Generate views
        for view in views:
            if inspect.isclass(view):
                self._reflect_views_from_class(view, injector, app)
            else:
                assert hasattr(view, '__view__')
                iview = InjectorView.as_view(view.__name__, handler=view, injector=injector)
                iview = self._install_route(injector, app, view, iview, *view.__view__)

    def _reflect_views_from_class(self, cls, injector, app):
        class_view = getattr(cls, '__view__', None)
        assert class_view is None or len(class_view[0]) == 1, \
            'Path prefix is the only non-keyword argument allowed on class @view for ' + str(cls)
        prefix = class_view[0][0] if class_view is not None else ''
        class_kwargs = class_view[1]
        for name, method in inspect.getmembers(cls, lambda m: inspect.ismethod(m) and hasattr(m, '__view__')):
            args, kwargs = method.__view__
            args = (prefix + args[0],) + args[1:]
            kwargs = dict(class_kwargs, **kwargs)
            iview = InjectorView.as_view(name, handler=method, injector=injector, handler_class=cls)
            self._install_route(injector, app, method, iview, args, kwargs)

    def _install_route(self, injector, app, view, iview, args, kwargs):
        if hasattr(view, '__decorators__'):
            for state in view.__decorators__:
                iview = state.apply(injector, iview)
        app.add_url_rule(*args, view_func=iview, **kwargs)
