#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
the script to run okaybuy crawlers
"""

import logging
import sys

import bee
import okaybuy


def crawl_okaybuy(logger, store_name):
    job_rules = okaybuy.gen_job_rules(store_name)
    bee.run_job(job_rules, max_idle_cnt=3, job_status_interval=3, logger=logger)

if __name__ == '__main__':
    logger = bee.init_logger("", logging.INFO)
    crawl_okaybuy(logger, 'okaybuy')
