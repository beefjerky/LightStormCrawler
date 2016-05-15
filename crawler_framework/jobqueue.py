import redis
import config

red = redis.StrictRedis(host=config.redis_host, port=config.redis_port, db=config.jobqueue_db)

class Queue:
    def __init__(self, name='jobqueue'):
        self.qname = name

    def reset(self):
        red.delete(self.qname)

    def enqueue(self, s):
        red.rpush(self.qname, s)
 
    def front_enqueue(self, s):
        red.lpush(self.qname, s)

    def dequeue(self):
        return red.lpop(self.qname)
 
    def length(self):
        return red.llen(self.qname)
