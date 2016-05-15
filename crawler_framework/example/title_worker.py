#coding:utf-8
import sys
import datetime
import time
import traceback
import simplejson as json

from crawler_framework.loop import loop
from crawler_framework.Logger import openlog, ERR, INFO, DBG
import logging
import codecs
import crawler_framework.config as config
from crawler_framework.stats import stats
from crawler_framework.jobqueue import Queue
from crawler_framework.page import get_page
import re

def worker(url):
    '''crawler worker'''
    try:
        r = get_page(url)
        title = re.search('<title>(.*)</title>', r).group(1)
        f.write('%s\x01%s\n'%(url, title))
    except:
        ERR('worker failed', traceback.format_exc())
        stats['job']['err']['exception'] = stats['job']['err'].get('exception', 0) + 1


if __name__ == '__main__':
    ts = sys.argv[1]
    try:
        part_id = int(sys.argv[2])
    except:
        part_id = 1

    f = codecs.open('%s_%s_%d.txt' % ('title', ts, part_id), 'w', encoding='utf-8')

    openlog("%s_%s_%d.log" % ('title', ts, part_id), level=logging.DEBUG, part_id=part_id)

    jq = Queue(config.jobname)

    loop(worker, n_threads=20, jq=jq)

    f.close()

