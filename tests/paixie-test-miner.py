#!/usr/bin/env python
# -*- coding: utf-8 -*-


import logging

import bee
import paixie


if __name__ == '__main__':

    logger = bee.init_logger("", logging.DEBUG)


    bee.test_miner(logger, "paixie.PaixieItemMiner", "file:./paixie-item.html", 'gb2312')
    #bee.test_miner(logger, "paixie.PaixieItemMiner", "http://www.paixie.net/product/325354.html", 'gb2312')
    
