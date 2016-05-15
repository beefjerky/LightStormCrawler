#!/bin/bash
function checkresult {
    if [ $? -ne 0 ]; then
        ret=$?
        cd crawler_framework; python mail.py "$1" $ret
        exit $ret
    fi
}

if [ $# -eq 1 ]; then
    ts=$1
else
    ts=`/bin/date +%Y_%-m_%-d`
fi



echo $ts


/usr/bin/python prepare_title.py $ts 
checkresult "prepare fail"

i=1
dir_name=`pwd`
echo $dir_name

cd ${dir_name}/crawler_framework; python update_proxy.py title_worker &
cd $dir_name; python title_worker.py ${ts} $i

