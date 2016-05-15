#coding:utf-8
import os
import sys

work_dir = os.getcwd()
if 'crawler_framework' not in work_dir:
    print 'please deploy under crawler_framework'
    sys.exit(1)
os.system('cp example/start.sh example/title_worker.py example/prepare_title.py example/job_config.py  example/stop.sh ../.')
os.system('chmod +x ../start.sh')
os.system('chmod +x ../stop.sh')
