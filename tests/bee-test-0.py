#!/usr/bin/env python
import logging

import bee

def test_fetcher(url, from_encoding, logger, unicode_errors='strict'):
    logger.debug("Test fetching: %s", url)

    fetcher = bee.SimpleHTTPFetcher(logger, from_encoding=from_encoding, unicode_errors=unicode_errors, user_agent="Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 6.2; Trident/4.0; SLCC2; .NET CLR 2.0.50727; .NET CLR 3.5.30729; .NET CLR 3.0.30729; Media Center PC 6.0)")
    (status_code, page) = fetcher.fetch(url)

    if page:
        logger.debug("RESPONSE url: %s", page.url)
        logger.debug("RESPONSE content_type: %s", page.content_type)
        logger.debug("RESPONSE encoding: %s", page.soup.originalEncoding)
        logger.debug("RESPONSE soup: %s", page.soup.renderContents()[:1000])
    else:
        logger.error("Failed to retrieve: %s: %s", url, status_code)


if __name__ == '__main__':

    logger = bee.init_logger("", logging.DEBUG)

#    test_fetcher("file:demosite/index.html", 'utf-8', logger)
#    test_fetcher("file:./taobao-item-detail.htm", 'gbk', logger)
#    test_fetcher("http://gracegift.taobao.com", 'gbk', logger)
#    test_fetcher("http://xiezi.com", 'utf-8', logger)
#    test_fetcher("http://taoxie.cn", 'utf-8', logger)
#    test_fetcher("http://paixie.net", 'gb2312', logger)
#    test_fetcher("http://www.okaybuy.com.cn/list.php?top_key=&curpage=11", "gbk", logger)
    test_fetcher("http://www.okaybuy.com.cn/com/16891657.html", "gbk", logger, 'replace')
