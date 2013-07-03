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
def main(injector):
    print 'Hello world'
```

### Injecting modules

A slightly more complex example injecting the logging module:

```python
from waffle import LoggingModule, main

@main(debug=True)
@modules(LoggingModule)
def main(injector):
    ...
```

### Multi-command

An application supporting multiple commands. Each command has its own set of modules defined. To remain DRY, @modules calls can be stacked and as this example shows, it's easy to set a default set of modules on all commands.

```python
from waffle import LoggingModule, LogLevel, flag, command, modules, run


default_modules = modules(LoggingModule)


@command
@flag('--pidfile', help='Path to PID file.')
@default_modules
def start(injector):
    print injector.get(LogLevel)


@command
@default_modules
def stop(injector):
    pass


run(log_level='warning')
```

`@main` and `run()` should be the last statements in the module.

### A full example web server with database

This example also shows how to set defaults for flags, by passing the flags as keyword arguments to either `main()` or `run()`.


```python
from flask import Flask
from injector import inject
from sqlalchemy import Column, String

from waffle import AppModules, WebModules, Base, Template, \
    controllers, route, main, modules


class KeyValue(Base):
    key = Column(String, primary_key=True)
    value = Column(String)


@route('/')
@inject(template=Template('index.html'))
def index(template):
    return template()


@route('/foo')
@inject(template=Template('foo.html'))
def foo(template):
    return template()


@main(database_uri='sqlite:///:memory:', static_root='./static/',
      template_root='./templates/')
@controllers(index, foo)
@modules(AppModules, WebModules)
def main(injector):
    app = injector.get(Flask)
    app.run()

```

## Available modules

### waffle.common.AppModules

Installs `waffle.db.DatabaseModule` and `waffle.db.LoggingModule`.

### waffle.web.common.WebModules

Installs `waffle.web.flask.FlaskModule`, `waffle.web.db.DatabaseSessionModule`, and `waffle.web.template.TemplateModule`.

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

### waffle.web.db.DatabaseSessionModule

A module that manages DB session lifecycle in Flask requests. This basically resets the session at the end of each request.

### waffle.web.template.TemplateModule

A module that provides template loading and the ability for separate modules to contribute to the global template rendering context. Useful for eg. adding global debug variables, etc.

To contribute to global template context:

```python
binder.multibind(TemplateContext, to={
    'debug': debug,
})
```

To inject a compiled template:

```python
@inject(template=Template('index.html'))
def index(template):
    return template.render()
```

### waffle.redis.RedisModule

Provides a Redis client configured by flags:

```python
from redis import Redis

@inject(redis=Redis)
def get(redis):
    return redis.get('some_key')
```
