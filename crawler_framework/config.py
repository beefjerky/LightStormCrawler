import sys
sys.path.append('../')
import job_config

throttle_period = job_config.throttle_period

redis_host = job_config.redis_host

redis_port = job_config.redis_port

jobqueue_db = job_config.jobqueue_db

proxy_db = job_config.proxy_db

jobname = job_config.jobname 

mongo_queue_dbname = job_config.__dict__.get('mongo_queue_dbname', None)

proxy_lists = job_config.proxy_lists

mongodb_host = job_config.mongodb_host
    
domain_map = job_config.__dict__.get('domain_map', {})

re_domain = job_config.__dict__.get('re_domain', {})

page_integrity_map = job_config.__dict__.get('page_integrity_map', {})


ratelimit_map = job_config.__dict__.get('ratelimit_map', {})

header_integrity_map = job_config.__dict__.get('header_integrity_map', {})

mailto_list = job_config.mailto_list

from_mail = job_config.from_mail


if __name__ == '__main__':
    for x in globals().keys():
        if not x.startswith('__') and x !='job_config':
            print x, globals()[x]
