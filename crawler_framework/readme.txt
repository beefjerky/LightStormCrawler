1.框架部署：
必须在爬虫框架目录执行python deploy.py，会在框架外层目录部署基本的使用示例，包括start.sh(启动脚本), stop.sh(停止脚本), prepare_title.py, title_worker.py, job_config.py(配置文件) 使用爬虫框架时可以直接在例子上修改。
部署完成后执行./start.sh即可

2.配置文件：
用户的配置直接修改job_config.py, 参数具体如下：
redis_host  => redis的主机名(job和代理管理)
redis_port  => redis的端口号
jobqueue_db => job的db
proxy_db => proxy的db
jobname => job的name
proxy_lists => 私有代理和野代理，例：'private': ('proxy', 'squids3', 0, 0) proxy：db名， squids3:表名 , skip, limit
mongodb_host => mongodb主机名
mongo_queue_dbname => 使用mongodb管理job时的db名
ratelimit_map => 限速配置 key->value key:域名 value:被限速的判断函数
domain_map => 代理配置 key->value  key:域名 value(10秒访问数限制， private，wild)
re_domain => 正则表达式判断域名列表 key->value key:正则 value:域名
page_integrity_map => 页面完整性判断 key->value key:域名 value:判断函数
header_integrity_map => header正确性判断 key->value key:域名 value:判断函数
mailto_list => 邮件发送地址
from_mail =>邮件配置


3.各接口介绍
1)Queue:
两种Queue类型jobqueue_mongodb 和 jobqueue
jobqueue_mongodb使用mongodb管理job,需要在配置时添加mongo_queue_dbname，当job长度比较长时，建议使用jobqueue_mongodb
jobqueue使用redis控制job

主要方法：
reset： 重制jobqueue
enqueue: push job 将jobworker的参数加入队列
dequeue: pop job 去重jobworker的参数
length: 剩余job数量
例子：jq = jobqueue.Queue('test')
jq.reset()
jq.enqueue(json.dumps('id':'123'))
word = jq.dequeue()

2)get_page(url, cookiejar = None, post_data = None, max_retry = 5, timeout = 10, referer = None, need_proxy = True, add_headers = {}, need_header = False, redirect = False, need_url = False)
获取页面的函数
参数：
url：链接地址
cookiejar：cookieJar对象， 默认为None
post_data: 使用post方法时使用, 默认为None
max_retry: 获取页面最大重试次数,默认为5
timeount: 超时时间
referer： referer地址, 默认为None
need_proxy： 是否需要使用proxy，默认为True
add_header: 需要添加的request header ,默认为{}
need_header: 结果是否需要返回response header，默认为False
redirect: 微博页面使用，其他不需要，都设为False
need_url: 是否需要返回页面实际的url, 默认为False
备注：
need_header == True and need_url=False时， 返回 (page, header)
need_header == True and need_url=True时， 返回 (page, header， url)
need_header == False and need_url=True, 返回 (page,url)
need_header == False and need_url=False时 返回 page

3) head_page(url, cookiejar=None, referer=None, add_headers={}, max_retry=10, need_proxy = True)
只需要header时使用， 返回header和currenturl
参数：
url：链接地址
cookiejar：cookieJar对象， 默认为None
referer： referer地址, 默认为None
add_header: 需要添加的request header ,默认为{}
need_proxy： 是否需要使用proxy，默认为True
max_retry: 获取页面最大重试次数,默认为10


4)loop(worker_func, n_threads=100, jq=jobqueue.Queue())
爬虫线程管理
参数:
worker_func: 线程的工作函数
n_threads:每个进程起的线程数， 默认100
jq：任务队列
使用方法：
jq = Queue(config.jobname)
loop(worker, n_threads=20, jq=jq)

5)ThrottleManager
代理控制
使用redis对代理使用进行管理，使用滑窗方式记录每个代理在每个域名下的使用次数，目前窗口大小设置为10s，选择代理时，根据url的域名，选择一个在窗口范围内使用次数小于配置次数的代理返回。当get_page时遇到代理被限速，需要调用flood_proxy。
主要方法：
update_proxylist：更新代理列表
get_domain_and_window： 获取域名和窗口大小
dump_proxy_logs：代理日志
choose_proxy： 选择代理
flood_proxy：代理限速

6)update_proxy.py
job运行过程中，每10分钟对redis中的代理进行refresh

7)uucheckcode.py
打验证码的接口，具体见uucheckcode.py介绍


8)Logger.py
日志接口，主要方法：
openlog:
ERR: error log
INFO: info log
DBG: debug log

9) mail.py
发送邮件的接口
主要方法：
mail(title, content)：title:邮件标题 content：内容
需要在job_config.py 配置    from_mail     tolist 

10) stats.py
job统计

11) deploy.py
示例代码部署，必须在爬虫框架目录下执行
