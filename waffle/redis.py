from __future__ import absolute_import
from redis import Redis
from injector import Module, singleton, provides

from waffle.flags import Flag


class RedisModule(Module):
    """Provides a Redis connection."""

    redis_server = Flag('--redis_server', default='localhost:6379:0', help='Host:port:db of Redis server.', metavar='HOST:PORT:DB')

    @provides(Redis, scope=singleton)
    def provide_redis(self):
        host, port, db = self.redis_server.split(':')
        port, db = int(port), int(db)
        return Redis(host, port, db)
