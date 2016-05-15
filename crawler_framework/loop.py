import threading
import time
import simplejson as json

from Logger import openlog, INFO, ERR, DBG


import jobqueue
from stats import stats, crawler
from page import dump_stats, refresh_proxy


threads = []

def loop(worker_func, n_threads=100, jq=jobqueue.Queue()):
    # start stats dump thread
    crawler['complete'] = False
    threading.Thread(target=dump_stats).start()

    #if long_running:
    #    threading.Thread(target=refresh_proxy).start()


    # if initial job queue is too short, (job queue can be changed at runtime)
    # inner_loop can quit prematurely 
    while inner_loop(worker_func, n_threads, jq) != 'alldone':
        time.sleep(1)


    crawler['complete'] = True



def inner_loop(worker_func, n_threads=100, jq=None):
    
    count = 0
    t0 = time.time()

    line = jq.dequeue()

    # no active thread && no job left --> time to really quit.
    if line == None:
        return 'alldone'

    j = 0
    while line != None:

        args = json.loads(line)

        INFO( j, args)

        t = threading.Thread(target=worker_func, kwargs=args)
        t.start()
        threads.append(t)

        if len(threads) >= n_threads:
            freed = False
            while True:
                for i in reversed(range(0, len(threads))):
                    t = threads[i]
                    if not t.is_alive():
                        threads.pop(i)
                        freed = True
                        count += 1
                        INFO( 'total time', count, (time.time()-t0), (time.time()-t0)/count)

                if freed:
                    break
                time.sleep(0.1)

        line = jq.dequeue()
        j += 1


    # clean up remaining threads
    while True:
        for i in reversed(range(0, len(threads))):
            t = threads[i]
            if not t.is_alive():
                threads.pop(i)
                count += 1
                INFO( 'total time', count, (time.time()-t0), (time.time()-t0)/count, len(threads))

        if threads == []: break
        time.sleep(0.1)

