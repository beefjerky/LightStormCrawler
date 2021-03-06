#coding:utf-8

#管理job queue 和代理限速的redis
redis_host = 'redis'  
redis_port = 6379
jobqueue_db = 1
proxy_db = 2

#job名
jobname = 'title'

throttle_period = 10

#代理列表
proxy_lists = {
    'private': ('proxy', 'squids3', 0, 0),
    'wild': ('proxy', 'externalproxy', 100, 100)
}
mongodb_host = 'dbredis'
#用mongodb控制jobqueue使用的db名称
mongo_queue_dbname = 'title'

#判断限速的lambda函数
ratelimit_map = {
    #'item.taobao.com': lambda text: u'访问受限了' in text
}

#每个域名的代理速度和选择配置
domain_map = {
    'news.ifeng.com': (10, True, True),
    'finance.ifeng.com': (10, True, True)
}

#正则表达式判断域名列表
re_domain = {
    #'shop\d+\.taobao\.com': 'shop.taobao.com'
}

#判断页面内容是否正确
page_integrity_map = {
    'news.baidu.com': lambda text: u'百度' in text
}

#判断header是否正确
header_integrity_map = {
    #'item.taobao.com': lambda headers: u'at_nick' in headers or u'At_Nick' in headers
}

#邮件收发地址
mailto_list = ['']
from_mail = {'mail_user': '', 'mail_host': '', 'mail_pass': '', 'mail_postfix': ''}

#from crawler_framework.stats  import stats
#stats.update({'order': {'i': 0, 't': 0}}


