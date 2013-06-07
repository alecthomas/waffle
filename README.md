# Waffle - A Dependency-Injection-based Python Application Framework

Waffle provides common functionality for bootstrapping an application using [Injector](https://github.com/alecthomas/injector). It provides:

1. Command line flag parsing via argh.
2. Injection of flags.
3. Construction of the injector.

A bare bones application:

```python
from waffle import main

@main
def main(injector):
    print 'Hello world'
```

A slightly more complex example with injectable flags and some useful default logging:

```python
from waffle import main
from injector import Injector
from waffle.flags import FlagsModule, expects_obj
from waffle.log import LoggingModule

@main
@modules(LoggingModule)
def main(injector):
    ...
```

An application supporting multiple commands:

```python
from waffle.app import command, run

@command
def start(injector):
    pass

@command
def stop(injector):
    pass

run()
```

`@main` and `run()` should be the last statements in the module.

## Common patterns

### Setting defaults for flags

This can be done before executing the entry point, by passing the flags as keyword arguments to either `main()` or `run()`.

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
