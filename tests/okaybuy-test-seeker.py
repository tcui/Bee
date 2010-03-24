#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging

import bee

seed_url = "http://www.okaybuy.com.cn/list.php?code=001000000&gender=1"

rules = [
        ['^http://www.okaybuy.com.cn/list.php?code=\d+&gender=\d&curpage=\d+', 200, 14400, "simple_http_get", ["okaybuy_cat_seeker"], [], False,],
        ['^http://www.okaybuy.com.cn/com/\d+.html$', 201, 86400, "simple_http_get", [], ["okaybuy_item_miner"], False,],
]


def test_seeker(logger, seed_url, rules):
    kwarg = {
        "rules": rules,
    }

    bee.test_seeker(logger, "bee.RuleBasedSeeker", seed_url, **kwarg)
 


if __name__ == '__main__':

    logger = bee.init_logger("", logging.DEBUG)

    test_seeker(logger, seed_url, rules)
