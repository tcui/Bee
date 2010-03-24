#!/usr/bin/env python
# -*- coding: utf-8 -*-


import logging

import bee
import okaybuy


if __name__ == '__main__':

    logger = bee.init_logger("", logging.DEBUG)


    bee.test_miner(logger, "okaybuy.OkaybuyItemMiner", "file:./okaybuy-item.html", 'gb2312')
    #bee.test_miner(logger, "okaybuy.OkaybuyItemMiner", "http://www.okaybuy.com.cn/com/16891657.html", 'gb2312')
    
