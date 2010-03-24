#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging

import bee

seed_url = "http://www.paixie.net/shoes/goods/_______-1.html"

rules = [
    ['^http://www.paixie.net/shoes/goods/_______-\d+.html$', 500, 14400, "simple_http_get", ["paixie_cat_seeker"], [], False,],
    ['^http://www.paixie.net/product/\d+.html$', 500, 86400, "simple_http_get", [], ["paixie_item_miner"], False,],
]


def test_seeker(logger, seed_url, rules):
    kwarg = {
        "rules": rules,
    }

    bee.test_seeker(logger, "bee.RuleBasedSeeker", seed_url, **kwarg)
 


if __name__ == '__main__':

    logger = bee.init_logger("", logging.DEBUG)

    test_seeker(logger, seed_url, rules)
