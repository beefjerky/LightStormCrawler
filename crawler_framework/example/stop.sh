#!/bin/bash
ps -ef| grep title_worker | awk "{print \$2}" | xargs kill
