from __future__ import absolute_import
from redis import Redis
from injector import Module, singleton, provides, inject

from waffle.flags import Flag, flag

flag('--redis_server', default='localhost:6379:0', help='Host:port:db of Redis server.', metavar='HOST:PORT:DB')


class RedisModule(Module):
    """Provides a Redis connection."""

    @singleton
    @provides(Redis)
    @inject(redis_server=Flag('redis_server'))
    def provide_redis(self, redis_server):
        host, port, db = redis_server.split(':')
        port, db = int(port), int(db)
        return Redis(host, port, db)
