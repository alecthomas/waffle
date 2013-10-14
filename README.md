# Waffle - A Dependency-Injection-based Python Application Framework

Waffle provides common functionality for bootstrapping an application using [Injector](https://github.com/alecthomas/injector).

The general approach used by the Injector modules in Waffle is to use flags to configure the behaviour of objects exported by the modules. The flag defaults can (and sometimes must) be overridden by the `@main` decorator or `run()` function.

For example, `waffle.redis.RedisModule` relies on the flag `--redis_server` to connect to a Redis server, which defaults to `localhost:6379:0`. To configure and use the Redis module you might do something like this:

```python
from waffle import main

@main(redis_server='redis.domain.com:6379:1')
def main(injector):
    redis = injector.get(Redis)
```

Waffle provides:

1. Command line flag parsing via argh.
2. Injection of flags.
3. Construction of the injector.
4. A bunch of modules that provide different integration: Redis, SQLAlchemy, Flask, logging, etc.

## Examples

### A bare bones application

```python
from waffle import main

@main
def main():
    print 'Hello world'
```

### Injecting modules

A slightly more complex example injecting the logging module:

```python
from waffle import LoggingModule, main

@main(debug=True)
@modules(LoggingModule)
def main():
    ...
```

### Multi-command

An application supporting multiple commands. Each command has its own set of modules defined. To remain DRY, @modules calls can be stacked and as this example shows, it's easy to set a default set of modules on all commands.

```python
from waffle import LoggingModule, LogLevel, flag, command, modules, run
from injector import Injector


default_modules = modules(LoggingModule)


@command
@flag('--pidfile', help='Path to PID file.')
@default_modules
@inject(injector=Injector)
def start(injector):
    print injector.get(LogLevel)


@command
@default_modules
def stop():
    pass


run(log_level='warning')
```

`@main` and `run()` should be the last statements in the module.

### A full example web server with database

This example illustrates several aspects of Waffle:

- How to set defaults for flags by passing the flags as keyword arguments to either `main()` or `run()`.
- The use of the convenience Injector modules `AppModules` and `WebModules`, which install commonly used modules for applications and web applications, respectively. See [below](#available-modules) for details.

- Use of the `@transaction` decorator to wrap requests in an SQLAlchemy transaction.


```python
from injector import inject
from sqlalchemy import Column, String

from waffle import AppModules, WebModules, \
    Model, WebApplication, routes, main, modules, route, \
    transaction, csrf_exempt


class KeyValue(Model):
    key = Column(String, primary_key=True)
    value = Column(String)


@route('/')
@transaction
def index():
    return [(kv.key, kv.value) for kv in KeyValue.query.all()]


@route('/<key>')
@transaction
@csrf_exempt
def get_or_create(request, key):
    kv = KeyValue.query.filter_by(key=key).all()
    if kv:
        kv = kv[0]
    if request.method == 'POST':
        if kv:
            kv.value = request.data
        else:
            kv = KeyValue(key=key, value=request.data)
        kv.save()
        return {'status': 'OK'}

    return {'key': kv.key, 'value': kv.value}


@main(database_uri='sqlite:///:memory:', static_root='./static/',
      template_root='./templates/')
@modules(AppModules, WebModules)
@inject(app=WebApplication)
def main(app):
    app.serve(port=8081, use_reloader=False)

```

## Available modules

### waffle.common.AppModules (composite)

Installs `waffle.db.DatabaseModule` and `waffle.db.LoggingModule`.

### waffle.web.common.WebModules (composite)

Installs `waffle.web.clastic.WebModule`, `waffle.web.db.DatabaseSessionModule`, `waffle.web.template.TemplateModule` and `waffle.web.csrf.CsrfModule`.

### waffle.db.DatabaseModule

Configure SQLAlchemy to work with injection.

Binds a configured SQLAlchemy `Session` to the injector.

```python
from sqlalchemy.orm import String
from sqlalchemy.orm.session import Session
from waffle import DatabaseModule, Base, main, modules


class KeyValue(Base):
    key = String()
    value = String()


@main(database_uri='sqlite:///tmp/test.db')
@modules(DatabaseModule)
def main(injector):
    session = injector.get(Session)
    ...
```

### waffle.log.LoggingModule

Configures some default basic logging.

Binds the key `LogLevel` to the specified log level.

### waffle.devel.DevelModule

A module that binds the gevent `BackdoorServer`, allowing the developer to attach to a Python shell in the application.

Use like so:

```python
injector.get(BackdoorServer).start()
```

### waffle.web.clastic.WebModule

Integrates [Clastic](https://github.com/mahmoud/clastic) through an injector module. This is the core module for providing web application support.

### waffle.web.db.DatabaseSessionModule

A module that manages DB session lifecycle in HTTP requests. This basically resets the session at the end of each request.

### waffle.web.template.TemplateModule

A module that provides template loading and the ability for separate modules to contribute to the global template rendering context. Useful for eg. adding global debug variables, etc.

To contribute to global template context:

```python
binder.multibind(TemplateContext, to={
    'debug': debug,
})
```

### waffle.web.csrf.CsrfModule

Enable CSRF support in templates.

### waffle.redis.RedisModule

Provides a Redis client configured by flags:

```python
from redis import Redis

@inject(redis=Redis)
def get(redis):
    return redis.get('some_key')
```
