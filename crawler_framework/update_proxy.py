# -*- coding: utf-8 -*-
import traceback
import os
import sys
import time
import throttle_manager2 as throttle_manager
from  jobqueue import Queue
import config
tm = throttle_manager.ThrottleManager()

def refresh_proxy(jq):
    is_running = True
    t0 = time.time()
    while True:
        try:
            tm.update_proxylist()
        except:
            pass
        if jq.length() == 0:
            if is_running == False:
                return 
            else:
                is_running = False
        time.sleep(10*60)

if __name__ == '__main__':
    jq = Queue(config.jobname)
    refresh_proxy(jq)
