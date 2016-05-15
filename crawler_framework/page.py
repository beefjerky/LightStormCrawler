# -*- coding: utf-8 -*-
import traceback
import os
import time
import urlparse
import sys
import datetime
try:
    import simplejson as json
except:
    import json
import urllib2
from urllib import quote_plus
import codecs
import threading
import random
from StringIO import StringIO
import gzip
import re
import cookielib
import logging
try:
    import pyamf
    from pyamf.remoting.client import RemotingService
except: pass

import HTMLParser
hparser = HTMLParser.HTMLParser()

from lxml import etree

from Logger import openlog, DBG, INFO, ERR
import Logger

import throttle_manager2 as throttle_manager
from stats import stats, crawler

tm = throttle_manager.ThrottleManager()

import config
page_integrity_map = config.page_integrity_map
header_integrity_map = config.header_integrity_map

cookie_store = {}

def decode_safe(s, encode_type = None):
    if type(s) == unicode: return s
    if encode_type != None:
        try:
            return s.decode(encode_type)
        except Exception, e:
            pass
    try: return s.decode('gbk')
    except: pass
    try: return s.decode('utf-8')
    except: pass
    try: return s.decode('gb2312')
    except: pass
    try: return s.decode('gb18030')
    except: pass


def dump_stats():
    t0 = time.time()
    while not crawler['complete']:
        time.sleep(10)
        for k, v in stats.items():
            if 'i' in v:
                INFO('STATS:', k, v['i'], '%.4f' % (time.time()-t0), '%.4f' % v['t'], '%.4f' % ((time.time() - t0)/(v['i'] + 0.01)), '%.4f' % (v['t']/(v['i'] + 0.01)))
            if 'err' in v:
                INFO('ERR STATS:', k, *('%s:%d' % (kk, vv) for kk, vv in v['err'].items()))

        try:
            tm.dump_proxy_logs()
            pass
        except:
            pass

def refresh_proxy():
    t0 = time.time()
    while not crawler['complete']:
        time.sleep(10*60)
        try:
            tm.update_proxylist()
        except:
            pass



class GetRequest(urllib2.Request):
    def get_method(self):
        return "GET"


class GETRedirectHandler(urllib2.HTTPRedirectHandler):
    """
    Subclass the HTTPRedirectHandler to make it use our
    HeadRequest also on the redirected URL
    """
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if code in (301, 302, 303, 307):
            #INFO('redirect', newurl, headers)
            newurl = newurl.replace(' ', '%20')

            # 这个页面会导致无穷302循环, 替换成另外一个登陆页面. 反正后面都会当做需要登录来处理的
            if newurl.startswith('http://weibo.com/login'):
                newurl = 'http://login.sina.com.cn/sso/login.php'

            return GetRequest(
                newurl,
                headers=req.headers,
                origin_req_host=req.get_origin_req_host(),
                unverifiable=True
            )
        else:
            raise urllib2.HTTPError(req.get_full_url(), code, msg, headers, fp)



def get_page(url, cookiejar = None, post_data = None, max_retry = 5, timeout = 10, referer = None, need_proxy = True, add_headers = {}, need_header = False, redirect = False, need_url = False):
    t00 = time.time()
    DBG('get_page', url)

    domain, _ = tm.get_domain_and_window(url)
    page_integrity = page_integrity_map.get(domain)
    
    text = None
    for i in range(0, max_retry):
        try:

            t0 = time.time()
            handlers = []
            if need_proxy:
                squid = tm.choose_proxy(url)
                INFO('proxy', squid['name'], squid)
                DBG('choose_proxy time', time.time() - t0)
                proxy_handler = urllib2.ProxyHandler({'http': '%s:%d' % (squid['ip'], int(float(squid['port'])))})
                handlers.append(proxy_handler)
            else:
                squid = {'name': 'local'}
            if cookiejar != None:
                cookie_processor = urllib2.HTTPCookieProcessor(cookiejar)
                handlers.append(cookie_processor)
            if redirect:
                handlers.append(GETRedirectHandler())

            opener = urllib2.build_opener(*handlers)
            request = urllib2.Request(url)
            request.add_header('Accept-Encoding', 'gzip')
            request.add_header('Accept-Language', 'zh-CN,en-US,en')
            request.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 5.1) AppleWebKit/537.31 (KHTML, like Gecko) Chrome/26.0.1410.43 Safari/537.31')
            request.add_header('Accept', 'application/json,text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8,q=0.01')
            if referer != None:
                request.add_header('Referer', referer)
            if add_headers != {}:
                for k in add_headers:
                    request.add_header(k, add_headers[k])
            try:
                t0 = time.time()
                if post_data == None:
                    rsp = opener.open(request, timeout=timeout)
                else:
                    rsp = opener.open(request, timeout=timeout, data=post_data)
                current_url = rsp.geturl()
                rsp_text = rsp.read()
                DBG('network time', time.time() - t0, squid['name'])
            except Exception, e:
                stats['page']['err']['network'] += 1
                ERR('error_err', str(e), url)
                raise

            try:
                t0 = time.time()
                if rsp.info().get('Content-Encoding') == 'gzip':
                    buf = StringIO(rsp_text)
                    f = gzip.GzipFile(fileobj=buf)
                    rsp_text = f.read()

                if rsp.info().get('Content-Type') == 'application/x-shockwave-flash': 
                    text = rsp_text
                else:
                    content_type = rsp.info().get('Content-Type')
                    m = re.search('charset=(.*)$', content_type)
                    if m != None:
                        encode_type = m.group(1).lower()  
                        text = decode_safe(rsp_text, encode_type)
                    else:
                        text = decode_safe(rsp_text)
                DBG('decode time', time.time() - t0)
            except:
                stats['page']['err']['decode'] += 1
                raise
            
            if config.ratelimit_map.get(domain) and config.ratelimit_map[domain](text):
                ERR('flooding proxy', squid['name'], url, rsp.geturl())
                tm.flood_proxy(squid, url)
                stats['page']['err']['flood'] += 1
                text = None
                continue


            if page_integrity!= None: 
                if rsp.info().get('Content-Type') != 'application/x-shockwave-flash' and not page_integrity(text):
                    #print 'page tampered', squid['name'], url, rsp.geturl()
                    ERR('page tampered', squid['name'], url, rsp.geturl())
                    stats['page']['err']['tamper'] += 1
                    text = None
                    continue

            break
        except Exception, e:
            ERR(traceback.format_exc(), e)
            text = None
            continue

    stats['page']['i'] += 1
    stats['page']['t'] += time.time() - t00

    if i == max_retry-1 and text == None:
        ERR( ' ******************* retry count exceeded', url)
        stats['page']['err']['giveup'] += 1
        if need_header:
            if need_url:
                return None, None, None
            else:
                return None, None
        elif need_url:
            return None, None
        else:
            return None
    if need_header:
        if need_url:
            return text, rsp.info(), rsp.geturl()
        else:
            return text, rsp.info()
    elif need_url:
        return text, rsp.geturl()
    else:
        return text
    

class HeadRequest(urllib2.Request):
    def get_method(self):
        return "HEAD"
        
class HEADRedirectHandler(urllib2.HTTPRedirectHandler):
    """
    Subclass the HTTPRedirectHandler to make it use our 
    HeadRequest also on the redirected URL
    """
    def redirect_request(self, req, fp, code, msg, headers, newurl): 
        if code in (301, 302, 303, 307):
            #print 'redirect', newurl#, headers
            newurl = newurl.replace(' ', '%20')

            return HeadRequest(
                newurl,
                headers=req.headers, 
                origin_req_host=req.get_origin_req_host(),
                unverifiable=True
            )
        else: 
            raise urllib2.HTTPError(req.get_full_url(), code, msg, headers, fp)
            
def head_page(url, cookiejar=None, referer=None, add_headers={}, max_retry=10, need_proxy = True):

    t00 = time.time()
    DBG('head_page', url)

    domain, _ = tm.get_domain_and_window(url)
    header_integrity = header_integrity_map.get(domain)

    headers = None
    for i in range(0, max_retry):
        try:
            #print 'retry', i
            t0 = time.time()
            if need_proxy:
                squid = tm.choose_proxy(url)
                DBG('proxy', squid['name'])
                DBG('choose_proxy time', time.time() - t0)

            #squid = {'name': 'local', 'ip': '10.8.0.6', 'port': 8888}
                proxy_handler = urllib2.ProxyHandler({'http': '%s:%s' % (squid['ip'], int(squid['port']))})
            else:
                squid = {'name': 'local'}
                proxy_handler = None
            redirect_handler = HEADRedirectHandler()
            
            if cookiejar != None:
                cookie_processor = urllib2.HTTPCookieProcessor(cookiejar)
            else:
                if squid['name'] not in cookie_store:
                   cookie_store[squid['name']] = cookielib.CookieJar()
                cookie_processor = urllib2.HTTPCookieProcessor(cookie_store[squid['name']])

            if proxy_handler != None:
                opener = urllib2.build_opener(cookie_processor, proxy_handler, redirect_handler)
            else:
                opener = urllib2.build_opener(cookie_processor, redirect_handler)

            request = urllib2.Request(url)
            request.add_header('Accept-Encoding', 'gzip')
            request.add_header('Accept-Language', 'zh-CN,en-US,en')
            request.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 5.1) AppleWebKit/537.31 (KHTML, like Gecko) Chrome/26.0.1410.43 Safari/537.31')
            if referer != None:
                request.add_header('Referer', referer)
            for k, v in add_headers.items():
                request.add_header(k, v)

            try:
                t0 = time.time()
                rsp = opener.open(request, timeout=10)
                current_url = rsp.geturl()
                headers = rsp.info()
                DBG('network time', time.time() - t0)
            except Exception, e:
                stats['page']['err']['network'] += 1
                ERR('error_err', str(e))
                headers = None
                continue

            if header_integrity!= None: 
                if not header_integrity(headers):
                    ERR('page tampered', squid['name'], headers, url, rsp.geturl())
                    stats['page']['err']['tamper'] += 1
                    headers = None
                    continue

            break
        except Exception, e:
            ERR(traceback.format_exc(), e)
            headers = None
            continue

    stats['page']['i'] += 1
    stats['page']['t'] += time.time() - t00

    if headers == None:
        ERR( ' ******************* retry count exceeded', url)
        stats['page']['err']['giveup'] += 1
        return None, None

    return headers, current_url



def urlopen_with_timeout(*args):
    return urllib2.urlopen(*args, timeout=10)

def get_amf(url, service, *args):
    # AMF remoting
    #gateway = RemotingService(url, pyamf.AMF0, user_agent='Mozilla/5.0 (Windows NT 5.1) AppleWebKit/537.31 (KHTML, like Gecko) Chrome/26.0.1410.43 Safari/537.31')

    r = None
    for i in range(10):
        DBG('attempt', i)
        squid = tm.choose_proxy(url)
        DBG('proxy', squid['name'])

        gateway = RemotingService(url, pyamf.AMF0, user_agent='Mozilla/5.0 (Windows NT 5.1) AppleWebKit/537.31 (KHTML, like Gecko) Chrome/26.0.1410.43 Safari/537.31', opener=urlopen_with_timeout)
        #gateway.setProxy('10.8.0.10:8888')
        gateway.setProxy('%s:%s' % (squid['ip'], int(squid['port'])))

        service_handle = gateway.getService(service)
        try:
            r = service_handle(*args)
            if r == '':
                print 'amf empty result', url, service, args
                ERR('amf empty result', url, service, args)
                continue

            break
        except:
            print 'amf failure', url, service, args, traceback.format_exc()
            ERR('amf failure', url, service, args, traceback.format_exc()) 

    if r == None:
        ERR(' *************** retry count exceeded', url, service, args)

    return r


if __name__ == '__main__':
    openlog('page.log')
    x =    get_page(url, cookiejar = None, post_data = None, max_retry = 5, timeout = 10, need_proxy = True, add_headers = {'Referer':'http://www.taobao.com'}, need_header = False, redirect = False, need_url=True)
    print x
