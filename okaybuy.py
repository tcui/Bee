# -*- coding: utf-8 -*-

"""
Customized parsers for okaybuy



initial seed:

# "all shoes -> ordery be new"

"http://www.okaybuy.com.cn/list.php?code=001000000&odrby=new"

Catalog:

http://www.okaybuy.com.cn/list.php?code=001000000&odrby=new&curpage=1

Detail page:

http://www.okaybuy.com.cn/com/16891657.html


"""

import logging
import json
import re

import bee


class OkaybuyItemMiner(bee.Miner):
    """
    this is usable for all okaybuy items
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
            n = soup.find('ul', {"class":"title"})
            l = n.find('li', {"class":"fl"}).h1
            prod['prod_name'] = l.string
        except:
            self._logger.exception("Failed to extract prod_name for :%s", (prod['url'],))
            prod['error'] += "Failed to extract prod_name"

        #sku
        try:
            n = soup.find('ul', {"class":"title"})
            l = n.find(text=re.compile("SKU: "))
            prod['prod_sku'] = l.string
        except:
            self._logger.exception("Failed to extract prod_sku for :%s", (prod['url'],))
            prod['error'] += "Failed to extract prod_sku"

        #price and shippig
        try:
            n = soup.find('div', {"class":"txt1"})
            l = n.find('span', {"class":"market_pr"})
            if l:
                prod['prod_market_price'] = l.string
            l = n.find('span', {"class":"sale_pr"})
            if l:
                prod['prod_price'] = l.string

            l = n.find('dd', {"class":"fl"})
            if l:
                l = l.find('span', {"class":"black"})
                if l:
                    prod['shipping_cost'] = l.string
        except:
            self._logger.exception("Failed to extract prod price and shipping for :%s", (prod['url'],))
            prod['error'] += "Failed to extract prod price and shipping"

        #size
        try:
            n = soup.find('div', {"class":"txt2"})
            if n:
                n = n.find('p', {"class":"size"})

            if n:
                sizes = n.findAll('a')
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
            t = soup.find(text=re.compile('large_images\[1\].src     = "http://i.okaybuy.cn/images/com/l'))
            img_cnt = 0
            for s in t.split():
                m = re.search('http://i.okaybuy.cn/images/com/l/.+\.jpg', s)
                if m:
                    img_cnt += 1
                    prod['prod_img_f_%s' % img_cnt] = m.group()
        except:
            self._logger.exception("Failed to extract image for :%s", (prod['url'],))
            prod['error'] += "Failed to extract image; "



        prods.append(prod)
        return prods


def gen_job_rules(store_name='okaybuy'):
    okaybuy_encoding = 'gb2312'
    okaybuy_seed_url = "http://www.okaybuy.com.cn/list.php?code=001000000&odrby=new&curpage=1"
    okaybuy_seeker_rules = [
        ['^http://www.okaybuy.com.cn/list.php\?code=001000000&odrby=new&curpage=\d+', 200, 14400, "simple_http_get", ["okaybuy_cat_seeker"], [], False,],
        ['^http://www.okaybuy.com.cn/com/\d+.html$', 201, 86400, "simple_http_get", [], ["okaybuy_item_miner"], False,],
    ]
    okaybuy_job_rules = {
        "desc": "Crawling job for %s" % (store_name,),
        "name": store_name,
        "num_workers": 2,
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
                        "from_encoding": okaybuy_encoding
                    }
                }
            }
        },
        "seeker_factory": {
            "rules": {
                "okaybuy_cat_seeker": {
                    "class_name": "bee.RuleBasedSeeker",
                    "params": {
                        "rules": okaybuy_seeker_rules,
                    }
                },
            }
        },
        "miner_factory": {
            "rules": {
                "okaybuy_item_miner": {
                    "class_name": "okaybuy.OkaybuyItemMiner",
                    "params": {
                    }
                },
            }
        },
        "seed_tasks": [
            {
                "url": okaybuy_seed_url,
                "fetcher": "simple_http_get",
                "seekers": ["okaybuy_cat_seeker"], 
                "miners": [],
                "hop": 0,
                "revisit_interval": 14400,
            },
        ],
    }

    return okaybuy_job_rules

