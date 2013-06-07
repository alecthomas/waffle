# Waffle - A Dependency-Injection-based Python Application Framework

Waffle provides common functionality for bootstrapping an application using [Injector](https://github.com/alecthomas/injector). It provides:

1. Command line flag parsing via argh.
2. Injection of flags.
3. Construction of the injector.

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
from waffle import main
from waffle.log import LoggingModule

@main(debug=True)
@modules(LoggingModule)
def main(injector):
    ...
```

### Multi-command

An application supporting multiple commands:

```python
from waffle.app import command, run
from waffle.log import LoggingModule

@command
def start(injector):
    pass

@command
def stop(injector):
    pass

run(LoggingModule)
```

`@main` and `run()` should be the last statements in the module.

### A full example web server with database

This example also shows how to set defaults for flags, by passing the flags as keyword arguments to either `main()` or `run()`.


```python
from flask import Flask
from injector import inject
from sqlalchemy import Column, String

from waffle import main, modules
from waffle.devel import DevelModule
from waffle.log import LoggingModule
from waffle.db import DatabaseModule, Base
from waffle.web import FlaskModule, route, controllers
from waffle.web.template import TemplateModule, Template
from waffle.web.db import DatabaseSessionModule


class KeyValue(Base):
    __tablename__ = 'key_value'

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


@main(console_port=9999, database_uri='sqlite:///:memory:',
      static_root='./static/', template_root='./templates/')
@controllers(index, foo)
@modules(DevelModule, LoggingModule, DatabaseModule, DatabaseSessionModule,
         FlaskModule, TemplateModule)
def main(injector):
    app = injector.get(Flask)
    app.run()

```

## Available modules

### waffle.db.DatabaseModule

Configure SQLAlchemy to work with injection.

Binds a configured SQLAlchemy `Session` to the injector.

```python
from sqlalchemy.orm import String
from sqlalchemy.orm.session import Session
from waffle import main, modules
from waffle.db import DatabaseModule, Base


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

A module that starts the gevent `BackdoorServer`, allowing the developer to attach to a Python shell in the application.

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
