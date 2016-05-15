import pymongo
import config

db = pymongo.Connection(config.mongodb_host)[config.mongo_queue_dbname]

class Queue:
    def __init__(self, name='jobqueue'):
        self.qname = name

    def reset(self):
        db.drop_collection(self.qname)

    def enqueue(self, s):
        db[self.qname].insert({'d': s})

    def dequeue(self):
        r = db[self.qname].find_and_modify(query={}, remove=True)
        if r == None: return None
        else:
            return r['d']
   
    def end_request(self):
        db.connection.end_request()

    def length(self):
        return db[self.qname].count()

if __name__ == '__main__':
    jq = Queue()
    jq.reset()
    for i in range(10):
        jq.enqueue(i)
    print jq.dequeue()
    
