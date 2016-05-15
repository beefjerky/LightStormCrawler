import traceback
import time
import sys
import datetime
import json
import codecs
import threading
import random
import re
import urllib2
import urlparse
from StringIO import StringIO
import gzip

from Logger import openlog, DBG, INFO, ERR
import Logger

import config

import redis
red = redis.StrictRedis(host=config.redis_host, port=config.redis_port, db=config.proxy_db)

import pymongo
from pymongo import Connection

conn = Connection(config.mongodb_host)
#proxydb = conn.proxy
private_db = conn[config.proxy_lists['private'][0]]
wild_db = conn[config.proxy_lists['wild'][0]]


#throttle_period = 10   #seconds
throttle_period = config.throttle_period

domain_map = {
    'default': (0.1, True, True)
}

re_domain = {
}


domain_map.update(config.domain_map)
re_domain.update(config.re_domain)

class ThrottleManager:
    def __init__(self):
        self.keys = set()
        self.windows = {}
        self.proxies = {}

        #self.update_proxylist()

        self.get_proxy_lua = red.register_script('''
            local domain = KEYS[1]
            local group = KEYS[2]
            local window = tonumber(ARGV[1])
            local period = tonumber(ARGV[2])
            local t = tonumber(ARGV[3])
            local proxy = redis.call('zrangebyscore', domain .. group, 0, t)[1]

            if proxy == nil then
                return nil
            end

            local logkey = domain .. proxy

            -- add this new record
            redis.call('zadd', logkey, t, t)

            -- remove expired records
            local n = redis.call('zremrangebyscore', logkey, 0, t - period)
            -- redis.log(redis.LOG_NOTICE, redis.call('zcard', logkey) .. ' ' .. n)


            local oldest_in_window = redis.call('zrevrange', logkey, 0, window)[window]

            if oldest_in_window == nil then
                redis.call('zadd', domain .. group, t, proxy)
            else
                -- redis.log(redis.LOG_NOTICE, proxy .. oldest_in_window .. ' ' .. t .. ' ' .. (oldest_in_window + period))
                redis.call('zadd', domain .. group, oldest_in_window + period, proxy)
            end

            return proxy

        ''')


    def update_proxylist(self):
        private_db = conn[config.proxy_lists['private'][0]]
        wild_db = conn[config.proxy_lists['wild'][0]]
        self._proxylist = {'private': [x for x in private_db[config.proxy_lists['private'][1]].find().skip(config.proxy_lists['private'][2]).limit(config.proxy_lists['private'][3])], 'wild': [x for x in wild_db[config.proxy_lists['wild'][1]].find().skip(config.proxy_lists['wild'][2]).limit(config.proxy_lists['wild'][3])]}

        p_set = set(['%s:%s' % (x['ip'], x['port']) for x in self.proxylist()])
        w_set = set(['%s:%s' % (x['ip'], x['port']) for x in self.proxylist(True)])
        for domain in domain_map.keys():
            rate, private, wild = domain_map[domain]
            self.windows[domain] = rate * throttle_period

            for group in ['private', 'wild']:
                #if group == 'private' and private:
                #    plist = self.proxylist()
                #elif group == 'wild' and wild:
                #    plist = self.proxylist(True)
                #else:
                #    continue
                if group == 'private' and private:
                    pset = p_set
                elif group == 'wild' and wild:
                    pset = w_set
                else:
                    continue
                #pset = set(['%s:%s' % (x['ip'], x['port']) for x in plist])
                for p in red.zrange(domain + group, 0, -1):
                    if p not in pset:
                        red.zrem(domain + group, p)
                for p in pset:
                    red.zadd(domain + group, 0, p)
                #for squid in plist:
                #    red.zadd(domain + group, 0, '%s:%s' % (squid['ip'], squid['port']))
                #    self.proxies['%s:%s' % (squid['ip'], squid['port'])] = squid

           
        

    def get_domain_and_window(self, url):

        domain = urlparse.urlparse(url).hostname
        DBG('domain', domain)
        if domain in domain_map:
            return domain, int(domain_map[domain][0] * throttle_period)
        for p in re_domain:
            if re.search(p, url):
                return re_domain[p], int(domain_map[re_domain[p]][0] * throttle_period)
        #elif re.search('shop\d+\.taobao\.com/search.htm', url):
        #    return 'shop.taobao.com', int(domain_map['shop.taobao.com'][0] * throttle_period)

        #elif re.search('shop\d+\.taobao\.alimama\.com', url):
        #    return 'shop.alimama.com', int(domain_map['shop.alimama.com'][0] * throttle_period)

        return 'default', int(domain_map['default'][0] * throttle_period)#raise Exception(url)


    def proxylist(self, wildproxy=False):
        if not wildproxy:
            return self._proxylist['private']
        else:
            return self._proxylist['wild']

    def get_proxylist(self, domain, wildproxy=False):
        if not wildproxy:
            return red.zrange(domain+'private', 0, -1)
        else:
            return red.zrange(domain+'wild', 0, -1)


    def dump_proxy_logs(self):
        s = '\n'
        for domain in self.keys:
            private, wild = domain_map[domain][1:3]

            plist_private = []
            plist_wild = []
            if private:
                #plist_private = self.proxylist()
                plist_private = self.get_proxylist(domain)
            if wild:
                #plist_wild = self.proxylist(True)
                plist_wild = self.get_proxylist(domain, True)
            s += 'PROXY ' + domain + ': '
            used = 0
            total = 0
            used_wild = 0
            total_wild = 0
            for x in plist_private:
                red.zremrangebyscore(domain + '%s'%x, 0, time.time() - throttle_period)
                used_this = red.zcard(domain + '%s' % x)
                #red.zremrangebyscore(domain + '%s:%s' % (x['ip'], x['port']), 0, time.time() - throttle_period)
                #used_this = red.zcard(domain + '%s:%s' % (x['ip'], x['port']))
                total_this = self.windows[domain]
                used += used_this
                total += total_this 
                s += ('%s:%d/%d' % ('%s:%s' % (x['ip'], x['port']), used_this, total_this)) + ' '

            for x in plist_wild:
                red.zremrangebyscore(domain + '%s' % x, 0, time.time() - throttle_period)
                used_this = red.zcard(domain + '%s' % x)
                #red.zremrangebyscore(domain + '%s:%s' % (x['ip'], x['port']), 0, time.time() - throttle_period)
                #used_this = red.zcard(domain + '%s:%s' % (x['ip'], x['port']))
                total_this = self.windows[domain]
                used += used_this
                total += total_this
                used_wild += used_this
                total_wild += total_this


            if wild:
                s += ('wild:%d/%d' % (used_wild, total_wild)) + ' '
            s += '%.2f%%\n' % (used*100.0/total)

        INFO(s)


    def choose_proxy(self, url):
        return self._choose_proxy(*self.get_domain_and_window(url))

    def _choose_proxy(self, domain, window):

        t0 = time.time()
        if domain not in self.keys:
            self.keys.add(domain)
            self.windows[domain] = window
        private, wild = domain_map[domain][1:3]
        while True:
            if private:
                p = self.get_proxy_lua(keys=[domain, 'private'], args=[window, throttle_period, time.time()])
                if p != None:
                    return {'ip': p.split(':')[0], 'port': p.split(':')[1], 'name': 'private' + p}
            if wild:
                p = self.get_proxy_lua(keys=[domain, 'wild'], args=[window, throttle_period, time.time()])
                if p != None:
                    return {'ip': p.split(':')[0], 'port': p.split(':')[1], 'name': 'wild' + p}
            time.sleep(0.1)
            #return {'ip': ip, 'port': port, 'name': p}
            #if p in self.proxies:
            #    return self.proxies[p]
            #else:
                #time.sleep(0.1)
                #INFO('unknown proxy', p)
                #continue 
            #    ip, port = p.split(':')
            #    return {'ip': ip, 'port': port, 'name': p}
 
         


    def flood_proxy(self, proxy, url):
        return self._flood_proxy(proxy, *self.get_domain_and_window(url))

    def _flood_proxy(self, proxy, domain, window):
        # flood the queue so no one can use this proxy in 5 minutes.
        later = time.time() + 5 * 60

        group = 'wild' if proxy['name'].startswith('wild') else 'private'
        red.zadd(domain + group, later, '%s:%s' % (proxy['ip'], proxy['port']))
        #for i in range(window):
        #    red.zadd(domain + proxy['name'], later, later)



def test_choose():
    tm = ThrottleManager()
    openlog('throttle_test.log')
    for i in range(1000):
        t0 = time.time()
        tm.choose_proxy('http://item.taobao.com/item.htm?id=16614479411')
        print time.time() - t0

if __name__ == '__main__':
    for i in range(20):
        t = threading.Thread(target=test_choose)
        t.start()
    sys.exit(0)

    from checkcode_manager import CheckcodeManager
    
    ua = 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.97 Safari/537.11'

    tm = ThrottleManager()
    openlog('throttle_test.log')

    '''
    for i in range(15*15):
        tm.get_proxy('http://item.taobao.com/item.htm?id=16614479411')
    sys.exit(0)
    '''

    i = [0]
    t0 = time.time()
    flood_count = [0]
    def worker():
        urls = ['http://item.taobao.com/item.htm?id=16614479411', 'http://detail.tmall.com/item.htm?id=16085757759', 'http://tbskip.taobao.com']
   
        text = '' 
        network_t= 0
        choose_t = 0
        total_t = 0
        j = 0
        while True:
            j += 1
            for url in urls[2:3]:
                t = time.time()
                squid = tm.choose_proxy(url)
                choose_t += (time.time() - t)
                INFO( 'choose time', choose_t/j)
                t2 = time.time()



