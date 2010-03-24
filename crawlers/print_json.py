#!/usr/bin/env python

import json
import sys

if __name__ == '__main__':
    if len(sys.argv) == 1:
        fp = sys.stdin
    elif len(sys.argv) == 2:
        fp = open(sys.argv[1])
    else:
        print "Usage: %s [filename]"
        sys.exit(1)

    line_no = 0
    line = fp.readline()
    while line:
        line_no += 1
        try:
            d = json.loads(line)
            print "Line %s: %s" % (line_no, json.dumps(d, indent=4, ensure_ascii=False))
        except:
            print "Line %s: is not valid JSON" % (line_no,)
        line = fp.readline()
        

