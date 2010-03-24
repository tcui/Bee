#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
the script to run paixie crawlers
"""

import logging
import sys

import bee
import paixie


def crawl_paixie(logger, store_name):
    job_rules = paixie.gen_job_rules(store_name)
    bee.run_job(job_rules, max_idle_cnt=3, job_status_interval=3, logger=logger)

if __name__ == '__main__':
    logger = bee.init_logger("", logging.INFO)
    crawl_paixie(logger, 'paixie')
