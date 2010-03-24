#!/usr/bin/env python
import logging
import json
import os

import bee

def test_seeker_1(logger):
    kwarg = {
        "rules": [
            [ ".*/cat\d+\.html", 3, "simple_http_get", ["simple_seek"], [], False ],
            [ ".*prod\d+\.html", 1, "simple_http_get", [], ["simple_miner"], False ],
        ]
    }

    bee.test_seeker(logger, "bee.RuleBasedSeeker", "file://%s/demosite/index.html" % (os.path.abspath('.'),), **kwarg)
 

if __name__ == '__main__':

    logger = bee.init_logger("", logging.DEBUG)

    test_seeker_1(logger)
