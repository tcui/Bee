#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
the script to run taobao crawlers
"""

import logging
import sys

import bee
import taobao


def crawl_taobao(logger, store_name):
    job_rules = taobao.gen_job_rules(store_name)
    bee.run_job(job_rules, max_idle_cnt=3, job_status_interval=3, logger=logger)

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print "Usage: python %s store_name" % (sys.argv[0],)
        print "   store_name is the sub-domain such as: carephilly, maizhongfs.mall, gracegift"
        sys.exit(1)

    store_name = sys.argv[1]
    logger = bee.init_logger("", logging.INFO)
    crawl_taobao(logger, store_name)
