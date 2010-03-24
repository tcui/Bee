#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging

import bee
import taobao

#  
#  Catalog:
#  
#  http://gracegift.taobao.com/?price1=&price2=&search=y&pageNum=1&scid=0&keyword=&orderType=_time&old_starts=&categoryp=&pidvid=&viewType=list&isNew=&ends=
#  http://gracegift.taobao.com/?price1=&price2=&search=y&pageNum=2&scid=0&keyword=&orderType=_time&old_starts=&categoryp=&pidvid=&viewType=list&isNew=&ends=
#  
#  Detail page
#  http://item.taobao.com/auction/item_detail-0db1-a4cac5e9329bd6ca120af53b20290cfd.htm
#  
gracegift_seed_url = "http://gracegift.taobao.com/?price1=&price2=&search=y&pageNum=1&scid=0&keyword=&orderType=_time&old_starts=&categoryp=&pidvid=&viewType=list&isNew=&ends="

gracegift_rules = [
    ['^http://gracegift.taobao.com/?.*search=y.+pageNum=\d', 50, 3600, "simple_http_get", ["taobao_cat_seeker"], [], False,],
    ['^http://item.taobao.com/auction/item_detail-.*\.htm$', 51, 86400, "simple_http_get", [], ["taobao_item_miner"], False,],
]

ufo_seed_url = "http://maizhongfs.mall.taobao.com/?search=y&price1=&price2=&pageNum=1&scid=0&keyword=&old_starts=&categoryp=&pidvid=&orderType=_time&viewType=list&isNew=&ends="

ufo_rules = [
    ['^http://maizhongfs.mall.taobao.com/?.*search=y.+pageNum=\d', 50, 3600, "simple_http_get", ["taobao_cat_seeker"], [], False,],
    ['^http://item.taobao.com/auction/item_detail-*\.htm$', 51, 86400, "simple_http_get", [], ["taobao_item_miner"], False,],
]


def test_seeker(logger, seed_url, rules):
    kwarg = {
        "rules": rules,
        "parent_node_type": "div",
        "parent_node_attrs": {"class":"shop-hesper"}
    }

    bee.test_seeker(logger, "bee.RuleBasedSeeker", seed_url, **kwarg)
 


if __name__ == '__main__':

    logger = bee.init_logger("", logging.DEBUG)

    # test_seeker(logger, "file:./taobao-gracegift-cat.html", gracegift_rules)
    test_seeker(logger, gracegift_seed_url, gracegift_rules)
    test_seeker(logger, ufo_seed_url, ufo_rules)
