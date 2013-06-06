from gevent import monkey
monkey.patch_all()

from injector import Module, inject
from flask import Flask

from app.db import Session


class DatabaseSessionModule(Module):
    """Manage SQLAlchemy session lifecycle."""

    @inject(app=Flask, session=Session)
    def configure(self, binder, app, session):
        # Ensure SQLAlchemy session is closed at the end of each request.
        @app.teardown_request
        def shutdown_session(exception=None):
            session.close()


# @command
# @arg('--address', help='Address to bind to [%(default)s].', default='127.0.0.1')
# @arg('--port', help='Port to bind to [%(default)s].', default=8000)
# @arg('--static_root', help='Root directory for static resources [%(default)s].',
#      metavar='DIR', default=DEFAULT_STATIC_ROOT)
# @expects_obj
# def run(args):
#     """Run the frontend webserver."""

#     print args

#     app = Flask(__name__, static_folder=args.static_root)
#     app.config.update(
#         SQLALCHEMY_DATABASE_URI=args.database_uri,
#     )
#     app.debug = args.debug

#     controllers = [index, socketio]
#     modules = [ArgsModule(args), LoggingModule, DevelModule, model.DatabaseModule, FrontendModule, TemplateModule]
#     builder = FlaskInjector(controllers, modules)
#     builder.init_app(app)

#     logging.info('Listening on http://%s:%s/' % (args.address, args.port))
#     try:
#         # TODO: Use silent logging class from pollute
#         server = SocketIOServer((args.address, args.port), app, resource="socket.io", policy_server=False)
#         server.serve_forever()
#     except KeyboardInterrupt:
#         sys.exit(1)


# if __name__ == '__main__':
#     conf.dispatch()
