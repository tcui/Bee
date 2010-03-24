# -*- coding: utf-8 -*-

"""
Customized parsers for Taobao.

All taobao stores are similar. 

We can rely on its search function to iterator through the inventory.
Basically, starts from "所有宝贝", "列表方式显示 ", "时间排序". The go to the
first page. Then you can get the initial seed page.

Each stores are only different by its store name, which is the sub-domain in url. Therefore, 
gen_job_rules() is provided to help generate the job rules to start the crawler.



initial seed:

http://gracegift.taobao.com/?price1=&price2=&search=y&pageNum=1&scid=0&keyword=&orderType=_time&old_starts=&categoryp=&pidvid=&viewType=list&isNew=&ends=

Catalog:

http://gracegift.taobao.com/?price1=&price2=&search=y&pageNum=1&scid=0&keyword=&orderType=_time&old_starts=&categoryp=&pidvid=&viewType=list&isNew=&ends=
http://gracegift.taobao.com/?price1=&price2=&search=y&pageNum=2&scid=0&keyword=&orderType=_time&old_starts=&categoryp=&pidvid=&viewType=list&isNew=&ends=

Detail page
http://item.taobao.com/auction/item_detail-0db1-a4cac5e9329bd6ca120af53b20290cfd.htm

"""

import logging
import json
import re

import bee


class TaobaoItemMiner(bee.Miner):
    """
    this is usable for all Taobao items
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
            n = soup.find('div', {"class":"detail-hd"}).h3.a
            prod['prod_name'] = n.string
            prod['sku_url'] = n['href']
        except Exception, e:
            prod['error'] += "failed to parse prod_name; "
            self._logger.exception("failed to parse prod_name for url: %s", prod['url'])

        #price
        try:
            n = soup.find('li', {"class":"detail-price clearfix"}).strong
            prod['prod_price'] = n.string
        except:
            prod['error'] += "failed to parse prod_price; "
            self._logger.exception("failed to parse prod_price for url: %s", prod['url'])

        #sold_amount
        try:
            n = soup.find('li', {"class":"sold-out clearfix"}).em
            prod['sold_amount'] = n.string
        except:
            prod['error'] += "failed to parse sold_amount; "
            self._logger.exception("failed to parse sold_amount for url: %s", prod['url'])

        #shipping cost
        try:
            n = soup.find('li', {"id":"ShippingCost", "class":"freight delivery clearfix"})
            if n:
                prod['shipping_cost'] = n.em.string
            else:
                n = soup.find('li', {"id":"J_PostageCont"})
                if n:
                    # shipping cost generated by javascript, cannot handler
                    prod['shipping_cost'] = 0.0
                else:
                    raise Exception("unknow case for shipping cost")
        except:
            prod['error'] += "failed to parse shipping_cost; "
            self._logger.exception("failed to parse shipping_cost for url: %s", prod['url'])
        
        #details
        try:
            n = soup.find('ul', {"class":"attributes-list"})
            attrs = n.findAll('li')
            attr_list = []
            for attr in attrs:
                if attr.has_key('title'):
                    attr_list.append({"attr_name": attr['title'], "attr_value": attr.string.replace("\t", "").replace("&nbsp", " ").replace("\r\n", "") })
            prod['prod_details'] = attr_list
        except:
            prod['error'] += "failed to parse details; "
            self._logger.exception("failed to parse details for url: %s", prod['url'])

        #images
        try:
            n = soup.find('ul', {"id":"J_UlThumb", "class":"thumb clearfix"})
            images = n.findAll('img')
            i = 0
            for image in images:
                prod["prod_img_s_%s" % (i,)] = image["src"]
                #full size image
                prod["prod_img_f_%s" % (i,)] = re.sub('_\d+x\d+\.jpg$', "", image["src"])
                i += 1
        except:
            prod['error'] += "failed to get images; "
            self._logger.exception("failed to parse image for url: %s", prod['url'])

        prods.append(prod)
        return prods


def gen_job_rules(store_name):
    taobao_encoding = 'gb2312'
    taobao_seed_url = "http://%s.taobao.com/?price1=&price2=&search=y&pageNum=1&scid=0&keyword=&orderType=_time&old_starts=&categoryp=&pidvid=&viewType=list&isNew=&ends=" % (store_name,)
    taobao_seeker_rules = [
    ["^http://%s.taobao.com/?.*search=y.+pageNum=\d" % (store_name,) , 50, 14400, "simple_http_get", ["taobao_cat_seeker"], [], False,],
    ['^http://item.taobao.com/auction/item_detail-.+\.htm$', 51, 86400, "simple_http_get", [], ["taobao_item_miner"], False,],
]
    taobao_job_rules = {
        "desc": "Crawling job for Taobao-%s" % (store_name,),
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
                "name": "taobao.%s.task.db" % (store_name,),
            },
        },
        "linkdb": {
            "class_name": "bee.SqliteLinkDB",
            "params" : {
                "name": "taobao.%s.link.db" % (store_name,),
            }
        },
        "output": {
            "class_name": "bee.JsonDumper",
            "params": {
                "filename": "taobao.%s.prod.json" % (store_name,),
            }
        },
        "fetcher_factory": {
            "rules": {
                "simple_http_get": {
                    "class_name": "bee.SimpleHTTPFetcher",
                    "params": {
                        "timeout": 20,
                        "user_agent": "Bee: picking good stuffs",
                        "proxy_host": "",
                        "proxy_port": 0,
                        "from_encoding": taobao_encoding,
                    }
                }
            }
        },
        "seeker_factory": {
            "rules": {
                "taobao_cat_seeker": {
                    "class_name": "bee.RuleBasedSeeker",
                    "params": {
                        "rules": taobao_seeker_rules,
                        "parent_node_type": "div",
                        "parent_node_attrs": {"class":"shop-hesper"}
                    }
                },
            }
        },
        "miner_factory": {
            "rules": {
                "taobao_item_miner": {
                    "class_name": "taobao.TaobaoItemMiner",
                    "params": {
                    }
                },
            }
        },
        "seed_tasks": [
            {
                "url": taobao_seed_url, 
                "fetcher": "simple_http_get",
                "seekers": ["taobao_cat_seeker"], 
                "miners": [],
                "hop": 0,
                "revisit_interval": 14400,
            }
        ],
    }

    return taobao_job_rules
