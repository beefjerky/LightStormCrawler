#coding:utf-8
import sys
import traceback
import simplejson as json

from crawler_framework.jobqueue import Queue
import datetime, time
import crawler_framework.config as config
from crawler_framework.page import get_page
import lxml
from lxml import etree
from StringIO import StringIO
def prepare(jq):
    '''push seeds into queue'''
    url = 'http://www.ifeng.com/'
    text = get_page(url)
    parser = etree.HTMLParser()
    node = etree.parse(StringIO(text), parser)
    links = node.xpath('.//a')
    for a in links:
        link = a.get('href')
        jq.enqueue(json.dumps({'url': link}))



if __name__ == '__main__':
    ts = sys.argv[1]
    jobname = config.jobname
    jq = Queue(jobname)
    jq.reset()
    prepare(jq=jq)
