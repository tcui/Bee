# -*- coding: utf-8 -*-

"""
Customized parsers for paixie



initial seed:

http://www.paixie.net/shoes/goods/_______-1.html

Catalog:

http://www.paixie.net/shoes/goods/_______-1.html
http://www.paixie.net/shoes/goods/_______-100.html


Detail page:


http://www.paixie.com.cn/com/16891657.html

"""

import logging
import json
import re

import bee


class PaixieItemMiner(bee.Miner):
    """
    this is usable for all paixie items
    """

    def extract(self, page):
        prods = []
        if not page or not page.soup: return prods

        soup = page.soup

        prod = {}

        prod['url'] = page.url
        prod['error'] = ''

        #name
        try:
            n = soup.find('div', {"id":"areaPro"}).find('div', {"class":"info"})
            prod['prod_name'] = n.h1.string
        except:
            self._logger.exception("Failed to extract prod_name for :%s", (prod['url'],))
            prod['error'] += "Failed to extract prod_name"


        #price and shippig
        try:
            n = n.find('ul').findAll('li')
            prod['prod_brand'] = n[0].strong.string
            prod['prod_aution_type'] = n[1].span.string.strip()
            prod['prod_type'] = re.sub('[\t\r\n]', '', n[2].span.string)
            prod['prod_market_price'] = n[3].find('del').string
            prod['prod_price'] = n[4].span.span.string
        except:
            self._logger.exception("Failed to extract prod price and shipping for :%s", (prod['url'],))
            prod['error'] += "Failed to extract prod price and shipping"

        #size
        try:
            n = soup.find('div', {"id":"boxCollectionSize"}).find('ul', {"id":"jsListSize"})
            if n:
                sizes = n.findAll('li')
                if sizes:
                    size_list = []
                    for s in sizes:
                        size_list.append(s.string)
                    prod['size'] = ', '.join(size_list)
                
        except:
            self._logger.exception("Failed to extract size for :%s", (prod['url'],))
            prod['error'] += "Failed to extract size; "

        #images
        try:
            imgs = soup.find('div', {"id":"areaPro"}).find("div", {"class":"gallery"}).findAll('a', {"class":"jsGoodsGallery"})
            img_cnt = 0
            for i in imgs:
                img_cnt += 1
                prod['prod_img_f_%s' % img_cnt] = i['rel']
        except:
            self._logger.exception("Failed to extract image for :%s", (prod['url'],))
            prod['error'] += "Failed to extract image; "



        prods.append(prod)
        return prods


def gen_job_rules(store_name='paixie'):
    paixie_encoding = 'gb2312'
    paixie_seed_url = "http://www.paixie.net/shoes/goods/_______-1.html"
    paixie_seeker_rules = [
        ['^http://www.paixie.net/shoes/goods/_______-\d+.html$', 500, 14400, "simple_http_get", ["paixie_cat_seeker"], [], False,],
        ['^http://www.paixie.net/product/\d+.html$', 500, 86400, "simple_http_get", [], ["paixie_item_miner"], False,],
    ]
    paixie_job_rules = {
        "desc": "Crawling job for %s" % (store_name,),
        "name": store_name,
        "num_workers": 3,
        "worker_params": {
            "max_crawler_failed_cnt": 3, 
            "max_crawler_timeout": 30, 
            "crawler_retry_interval": 10, 
            "pause_on_reinject": 0.1, 
            "pause_before_fetch": 0, 
            "pause_when_notask": 0.1,
        },
        "task_queue": {
            "class_name": "bee.DBTaskQueue",
            "params": {
                "name": "%s.task.db" % (store_name,),
            },
        },
        "linkdb": {
            "class_name": "bee.SqliteLinkDB",
            "params" : {
                "name": "%s.link.db" % (store_name,),
            }
        },
        "output": {
            "class_name": "bee.JsonDumper",
            "params": {
                "filename": "%s.prod.json" % (store_name,),
            }
        },
        "fetcher_factory": {
            "rules": {
                "simple_http_get": {
                    "class_name": "bee.SimpleHTTPFetcher",
                    "params": {
                        "timeout": 20,
                        "user_agent": bee.DEFAULT_USER_AGENT,
                        "proxy_host": "",
                        "proxy_port": 0,
                        "from_encoding": paixie_encoding
                    }
                }
            }
        },
        "seeker_factory": {
            "rules": {
                "paixie_cat_seeker": {
                    "class_name": "bee.RuleBasedSeeker",
                    "params": {
                        "rules": paixie_seeker_rules,
                    }
                },
            }
        },
        "miner_factory": {
            "rules": {
                "paixie_item_miner": {
                    "class_name": "paixie.PaixieItemMiner",
                    "params": {
                    }
                },
            }
        },
        "seed_tasks": [
            {
                "url": paixie_seed_url, 
                "fetcher": "simple_http_get",
                "seekers": ["paixie_cat_seeker"], 
                "miners": [],
                "hop": 0,
                "revisit_interval": 14400,
            }
        ],
    }

    return paixie_job_rules

