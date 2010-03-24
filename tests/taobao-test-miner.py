#!/usr/bin/env python
# -*- coding: utf-8 -*-


import logging

import bee
import taobao




if __name__ == '__main__':

    logger = bee.init_logger("", logging.DEBUG)

    bee.test_miner(logger, "taobao.TaobaoItemMiner", "file:./taobao-item-detail.htm", 'gb2312')
    #bee.test_miner(logger, "taobao.TaobaoItemMiner", "http://item.taobao.com/auction/item_detail-0db1-e31b679f693be2a0beb9d60effcc54de.htm", 'gb2312')

    bee.test_miner(logger, "taobao.TaobaoItemMiner", "file:./taobao-item-detail2.htm", 'gb2312')
    #bee.test_miner(logger, "taobao.TaobaoItemMiner", "http://item.taobao.com/auction/item_detail-0db2-a5f51c7b6eba2842a4d58c3b377b4681.htm", 'gb2312')
    
