#!/usr/bin/env python
import logging
import json
import os
import re

import bee


class ProductMiner(bee.Miner):
    def extract(self, page):
        prods = []
        if not page or not page.soup: return prods

        body_text = page.soup.body.renderContents()

        prod = {}

        #self._logger.debug("extracting: %s", body_text)

        r =  re.search('(?<=name: )\w+', body_text)
        if r:
            prod['name'] = r.group(0)
        else:
            self._logger.debug("didn't find name: %s", body_text)
            return prods

        r =  re.search('(?<=price: )\$\d+', body_text)
        if r:
            prod['price'] = r.group(0)
        else:
            self._logger.debug("didn't find price: %s", body_text)
            return prods

        prods.append(prod)

        return prods



def test_simple_crawling_job(logger):

    seed_url = "file://%s/demosite/index.html" % (os.path.abspath('.'),)

    sample_job_rules = {
        "desc": "Example job, crawing the test site, extract prod desc", 
        "name": "sample",
        "num_workers": 1,
        "worker_params": {
            "max_crawler_failed_cnt": 3, 
            "max_crawler_timeout": 30, 
            "crawler_retry_interval": 10, 
            "pause_on_reinject": 0.1, 
            "pause_before_fetch": 0, 
            "pause_when_notask": 0.1,
        },
        "linkdb": {
            "class_name": "bee.SqliteLinkDB",
            "params" : {
                "name": "sample_site.link.db",
            }
        },
        "task_queue": {
            "class_name": "bee.MemTaskQueue",
            "params": {
            },
        },
        "output": {
            "class_name": "bee.JsonDumper",
            "params": {
                "filename": "sample_site.out.json"
            }
        },
        "fetcher_factory": {
            "rules": {
                "simple_http_get": {
                    "class_name": "bee.SimpleHTTPFetcher",
                    "params": {
                        "timeout": 10,
                        "user_agent": "Bee: picking good stuffs",
                        "proxy_host": "",
                        "proxy_port": 0,
                        "from_encoding": "utf-8"
                    }
                }
            }
        },
        "seeker_factory": {
            "rules": {
                "simple_seek": {
                    "class_name": "bee.RuleBasedSeeker",
                    "params": {
                        "rules": [
                            [ ".*/cat\d+\.html", 3, 60, "simple_http_get", ["simple_seek"], [], False ],
                            [ ".*prod\d+\.html", 1, 60, "simple_http_get", [], ["simple_miner"], False ],
                        ],
                    }
                },
            }
        },
        "miner_factory": {
            "rules": {
                "simple_miner": {
                    "class_name": "ProductMiner",
                    "params": {
                    }
                },
            }
        },
        "seed_tasks": [
            {
                "url": seed_url, 
                "fetcher": "simple_http_get",
                "seekers": ["simple_seek"], 
                "miners": [],
                "hop": 0,
                "revisit_interval": 60,
            }
        ]
    }

    bee.run_job(sample_job_rules, max_idle_cnt=3, job_status_interval=1, logger=logger)


 

if __name__ == '__main__':

    logger = bee.init_logger("", logging.DEBUG)

    test_simple_crawling_job(logger)
