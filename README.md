# Waffle - A Dependency-Injection-based Python Application Framework

A bare bones application:

	from waffle import main

	@main
	def main():
		print 'Hello world'

A slightly more complex example with injectable flags and some useful default logging:

	from waffle import main
	from injector import Injector
	from waffle.flags import FlagsModule, expects_obj
	from waffle.log import LoggingModule

	@main
	@expects_obj
	def main(args):
		injector = Injector([FlagsModule(args), LoggingModule, …])

An application supporting multiple commands:

	from waffle.app import command, run
	from waffle.flags import FlagsModule

	@command
	def start(args):
		pass

	@command
	def stop(args):
		pass

	run()

`@main` and `run()` should be the last statements in the module.

## Available modules

### waffle.db.DatabaseModule

Configure SQLAlchemy to work with injection.


	from injector import Injector
	from sqlalchemy.orm import String
	from sqlalchemy.orm.session import Session
	from waffle import main
	from waffle.flags import FlagsModule
	from waffle.db import DatabaseModule, Base


	class KeyValue(Base):
		key = String()
		value = String()


	@main(database_uri='sqlite:///tmp/test.db')
	def main(args):
		injector = Injector([FlagsModule(args), DatabaseModule])
		session = injector.get(Session)
		...

### waffle.log.LoggingModule

Configures some default basic logging.

### waffle.devel.DevelModule

A module that starts the gevent BackdoorServer, allowing the developer to attach to a Python shell in the application.


### waffle.web.db.DatabaseSessionModule

A module that manages DB session lifecycle in Flask requests.

### waffle.web.template.TemplateModule

A module that provides template loading and the ability for separate modules to contribute to the global template rendering context. Useful for eg. adding global debug variables, etc.

To contribute to global template context:

    binder.multibind(TemplateContext, to={
        'debug': debug,
    })

To inject a compiled template:

	@inject(template=Template('index.html'))
	def index(template):
		return template.render()
