"""
Bee -- only download good flowers from the Internet :-)
=========================================================

This crawler only download selective contents from the Internet. 
Therefore it is slightly different for the typical generic 
purpose crawler. 

The crawler behaviors are defined by "polices". 

"""

import cPickle
import logging
import Queue
import random
import re
import sqlite3
import sys
import threading
import time
import types
import urllib2
import urlparse
import json
import sys

from BeautifulSoup import BeautifulSoup
 

DEFAULT_USER_AGENT = "Bee: picking good stuffs"

############ utilities ############################

def init_logger(name, level=logging.INFO):
    """
    initialize logger
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    # create console handler and set level to debug
    ch = logging.StreamHandler()
    ch.setLevel(level)
    # create formatter
    if level == logging.DEBUG:
        formatter = logging.Formatter("%(asctime)s [%(levelname)s] [%(filename)s:%(lineno)s:%(thread)d] %(message)s")
    else:
        formatter = logging.Formatter("%(asctime)s [%(levelname)s] [%(filename)s:%(lineno)s] %(message)s")
    # add formatter to ch
    ch.setFormatter(formatter)
    # add ch to logger
    logger.addHandler(ch)
    return logger

######### class loader ########

def _get_mod(module_path):
    try:
        a_mod = sys.modules[module_path]
        if not isinstance(a_mod, types.ModuleType):
            raise KeyError
    except KeyError:
        # The last [''] is very important!
        a_mod = __import__(module_path, globals(), locals(), [''])
        sys.modules[module_path] = a_mod
    return a_mod

def _get_func(full_func_name):
    """Retrieve a function object from a full dotted-package name."""
    
    # Parse out the path, module, and function
    last_dot = full_func_name.rfind(u".")
    if last_dot == -1:
        func_name = full_func_name
        mode_path = '__main__'
    else:
        func_name = full_func_name[last_dot + 1:]
        mode_path = full_func_name[:last_dot]

    
    a_mod = _get_mod(mode_path)
    a_func = getattr(a_mod, func_name)
    
    # Assert that the function is a *callable* attribute.
    assert callable(a_func), u"%s is not callable." % full_func_name
    
    # Return a reference to the function itself,
    # not the results of the function.
    return a_func

def _get_class(full_class_name, parent_class=None):
    """Load a module and retrieve a class (NOT an instance).
    
    If the parent_class is supplied, className must be of parent_class
    or a subclass of parent_class (or None is returned).
    """
    a_class = _get_func(full_class_name)
    
    # Assert that the class is a subclass of parent_class.
    if parent_class is not None:
        if not issubclass(a_class, parent_class):
            raise TypeError(u"%s is not a subclass of %s" %
                            (full_class_name, parent_class))
    
    # Return a reference to the class itself, not an instantiated object.
    return a_class

_CLASS_CACHE = {}

def get_class_by_name(full_class_name, parent_class=None):
    if _CLASS_CACHE.has_key(full_class_name): return _CLASS_CACHE[full_class_name]

    a_class = _get_class(full_class_name, parent_class)
    _CLASS_CACHE[full_class_name] = a_class

    return a_class
      


################### Bee #################################

############## interfaces and base classes ###############

class InvalidRulesException(Exception):
    pass


class Page:
    """
    page object
    """
    def __init__(self, reply):
        """
        :Parameters:
            - reply: object returned by urllib2.urlopen()
        """
        self.url = reply.geturl().strip()
        self.content_type = reply.headers.get('content_type')
        self.expires = reply.headers.get('expires') #TODO to epoch time
        self.data = reply.read()


class HTMLPage (Page):
    """
    html page object
    """
    def __init__(self, reply, from_encoding='utf-8', unicode_errors=None):
        Page.__init__(self, reply)
        if not unicode_errors:
            if from_encoding:
                unicode_errors = 'replace'
            else:
                unicode_errors = 'strict'
        self.soup = BeautifulSoup(self.data, fromEncoding=from_encoding, unicodeErrors=unicode_errors)

class LinkDB:
    """
    record link visit history
    """
    def __init__(self, logger):
        self._logger = logger

    def get_status(self, url):
        """
        return (last_start_ts, last_end_ts, status_code, fail_cnt)
        """
        return (0, 0, '', 0)

    def mark_started(self, url):
        """
        Mark start crawling one url
        """
        return 

    def mark_ended(self, url, status_code=''):
        """
        Mark the end fo crawling one url
        """
        return

    def lock(self):
        pass

    def unlock(self):
        pass

    def started_cnt(self):
        return 0

    def succeeded_cnt(self):
        return 0

    def failed_cnt(self):
        return 0

class SqliteHelper:
    def __init__(self, name):
        self.__name = name
        self.__lock = threading.RLock()
        self.__conns = {}

    def _get_conn(self):
        conn = None
        self.__lock.acquire()
        try:
            thread_id = threading.current_thread()
            if self.__conns.has_key(thread_id):
                conn = self.__conns[thread_id]
            else:
                conn = sqlite3.connect(self.__name)
                self.__conns[thread_id] = conn
        finally:
            self.__lock.release()

        return conn

class SqliteLinkDB(LinkDB, SqliteHelper):
    def __init__(self, logger, name):
        if not name: raise Exception("Please provide linkdb name")
        LinkDB.__init__(self, logger)
        SqliteHelper.__init__(self, name)
        self.__lock = threading.RLock()
        self.__started_cnt = 0
        self.__succeeded_cnt = 0
        self.__failed_cnt = 0
        conn = self._get_conn()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS links (
                url VARCHAR(1000) PRIMARY KEY,
                last_start_ts DECIMAL DEFAULT 0,
                last_end_ts DECIMAL DEFAULT 0,
                last_status_code VARHCAR(64) DEFAULT "",
                failed_cnt INT DEFAULT 0
            )
            """)

    def get_status(self, url):
        cursor = self._get_conn().cursor()
        try:
            cursor.execute("SELECT last_start_ts, last_end_ts, last_status_code, failed_cnt FROM links WHERE url = ?", (url,))
            row = cursor.fetchone()
            if not row: return (0, 0, '', 0)
            return (row[0], row[1], row[2], row[3])
        finally:
            cursor.close()

    def mark_started(self, url):
        """
        Mark start crawling one url
        """
        self.__started_cnt += 1
        conn = self._get_conn()
        try:
            conn.execute("INSERT INTO links (url, last_start_ts) VALUES (?, ?)", (url, time.time(),))
        except sqlite3.IntegrityError, m:
            conn.execute("UPDATE links SET last_start_ts = ? WHERE url = ?", (time.time(), url,))
        conn.commit()

    def mark_ended(self, url, status_code=''):
        """
        Mark the end fo crawling one url
        """
        conn = self._get_conn()
        try:
            if status_code:
                self.__failed_cnt += 1
                conn.execute("INSERT INTO links (url, last_end_ts, last_status_code, failed_cnt) VALUES (?, ?, ?, 1)", (url, time.time(), status_code))
            else:
                self.__succeeded_cnt += 1
                conn.execute("INSERT INTO links (url, last_end_ts, last_status_code, failed_cnt) VALUES (?, ?, '', 0)", (url, time.time(),))
        except sqlite3.IntegrityError, m:
            if status_code:
                conn.execute("UPDATE links SET last_end_ts = ?, last_status_code = ?, failed_cnt = failed_cnt + 1 WHERE url = ?", (time.time(), status_code, url,))
            else:
                conn.execute("UPDATE links SET last_end_ts = ?, last_status_code = '', failed_cnt = 0 WHERE url = ?", (time.time(), url,))
        conn.commit()

    def lock(self):
        self.__lock.acquire()

    def unlock(self):
        self.__lock.release()

    def started_cnt(self):
        return self.__started_cnt

    def succeeded_cnt(self):
        return self.__succeeded_cnt

    def failed_cnt(self):
        return self.__failed_cnt


class Output:
    """
    save the objects 
    """
    def __init__(self, logger):
        self._logger = logger

    def write(self, obj_dict):
        raise Exception("Please implement me")

    def flush(self):
        pass

    def close(self):
        pass

    def count(self):
        return 0


class JsonDumper(Output):
    """
    Output obj_diict as json string
    """
    def __init__(self, logger, filename, indent=None, ensure_ascii=True):
        Output.__init__(self, logger)
        self.__filename = filename
        self.__indent = indent
        self.__ensure_ascii = ensure_ascii
        self.__cnt = 0
        if self.__filename:
            self.__fp = open(filename, "a+")
        else:
            self.__fp = sys.stdout

        self.__lock = threading.RLock()


    def count(self):
        return self.__cnt

    def write(self, obj_dict):
        self.__lock.acquire()
        try:
            self.__cnt += 1
            if self.__fp:
                self.__fp.write("%s\n" % (json.dumps(obj_dict, indent=self.__indent, ensure_ascii=self.__ensure_ascii),))
        finally:
            self.__lock.release()

    def flush(self):
        self.__lock.acquire()
        try:
            if self.__fp: self.__fp.flush()
        finally:
            self.__lock.release()

    def close(self):
        self.__lock.acquire()
        try:
            if self.__fp:
                self.__fp.close()
                self.__fp = None
        finally:
            self.__lock.release()

class Fetcher:
    """
    Base class that retrieve content for given URL

    The instance of fetcher class my be shared by multiple threads. 

    """
    def __init__(self, logger):
        self._logger = logger

    def fetch(self, url):
        """
        retrieve content for the given url

        :Parameter:
            - `url`: the location of the resource
            - `timeout`: maximum wait period. 0 means wait forever

        :Return:
            (status_code, Page object)
        """
        raise Exception("Please impelent me")


class SimpleHTTPFetcher (Fetcher):
    """
    Fetch http:// resource
    """
    def __init__(self, logger, from_encoding='utf-8', unicode_errors=None, user_agent=DEFAULT_USER_AGENT, proxy_host=None, proxy_port=None, timeout=10):
        Fetcher.__init__(self, logger)
        self.__from_encoding = from_encoding
        self.__unicode_errors = unicode_errors
        self.__user_agent = user_agent
        self.__proxy_host = proxy_host
        self.__proxy_port = proxy_port
        self.__timeout = timeout

    def _prepare_request(self, request):
        request.add_header("User-Agent", self.__user_agent)
        if (self.__proxy_host and self.__proxy_port):
            request.set_proxy(self.__proxy_host, self.__proxy_port)

    def fetch(self, url):
        """
        retrieve content for the given url

        :Parameter:
            - `url`: the location of the resource
            - `timeout`: maximum wait period. 0 means wait forever

        :Return:
            (status, Page Object)

        :TODO:
            - support authentication
        """
        self._logger.debug("Fetching %s (%s)", url, self.__timeout)

        request = urllib2.Request(url)

        # add headers
        self._prepare_request(request)

        status = ""
        page = None
        try:
            reply = urllib2.urlopen(request, timeout=self.__timeout)
            if reply is None:
                status = "ERROR UNKNOWN"
            else:
                # leave status as empty string if successful 
                page = self._build_page(reply)
        except urllib2.HTTPError, error:
            if error.code == 404:
                self._logger.error("Fetcher HTTPError: %s -> %s", error, error.url)
            else:
                self._logger.error("Fetcher HTTPError: %s", error)

            status = "HTTP %s" % error
        except urllib2.URLError, error:
            self._logger.error("Fetcher URLError: %s", error)
            status = "URL %s" % error

        return (status, page)

    def _build_page(self, reply):
        """
        return Page object based on reply
        """

        content_type = reply.headers.get('content-type')
        if ( content_type.startswith('text/html')):
            try: 
                return HTMLPage(reply, from_encoding=self.__from_encoding, unicode_errors=self.__unicode_errors)
            except Exception, error:
                self._logger.debug("HTML page parsing error: %s", error)
        else:
            # REVIEW: to handle other data type
            # generate generic page object
            return Page(reply)

class Seeker:
    def __init__(self, logger):
        self._logger = logger

    def inspect(self, page, hop):
        return []

class RuleBasedSeeker(Seeker):
    """
    Seeker is to hunting useful urls in page. It generate 
    Additional Seeker tasks or Miner task base on the configuration

    This is a basic generic implementation. Feel free to subclass it
    when you need to customize its behavior
    """
    def __init__(self, logger, rules, parent_node_type=None, parent_node_attrs=None):
        """
        :Parameters:
            - rules: define the policy of the seeker
                
                [[regex, max_hop, next_seeker_tasks, next_minner_tasks, stop_if_matched,] , ]
        """
        Seeker.__init__(self, logger)
        self._rules = rules
        self._parent_node_type = parent_node_type
        self._parent_node_attrs = parent_node_attrs

    def inspect(self, page, hop):
        new_tasks = []

        if not page: return new_tasks
        if not isinstance(page, HTMLPage): return new_tasks

        parent_node = None
        if self._parent_node_type:
            if self._parent_node_attrs:
                parent_node = page.soup.find(self._parent_node_type, self._parent_node_attrs)
            else:
                parent_node = page.soup.find(self._parent_node_type)

        if parent_node:
            tags = parent_node('a')
        else:
            tags = page.soup('a')

        if not tags: return new_tasks
        
        for tag in tags:
            try:
                href = tag["href"]
                if href is not None:
                    url = urlparse.urljoin(page.url, href.strip())
                    self._inspect_url(url, hop + 1, new_tasks)
            except KeyError:
                pass
            
        return new_tasks

    def _inspect_url(self, url, hop, new_tasks):
        if not url: return
        self._logger.debug("evaluating: %s", url)
        for (regex, max_hop, revisit_interval, next_fetcher, next_seekers, next_miners, stop_if_matched) in self._rules:
            if not re.match(regex, url): 
                self._logger.debug("doesn't match: %s", regex)
                continue

            if next_seekers and hop > max_hop:
                self._logger.debug("hop %s > max_hop %s, do not seek further: %s", hop, max_hop, url)
                next_seekers = []

            if next_seekers or next_miners:
                new_tasks.append( {
                        "url": url, 
                        "revisit_interval": revisit_interval,
                        "fetcher": next_fetcher,
                        "seekers": next_seekers,
                        "miners": next_miners,
                        "hop": hop}
                    )

            if stop_if_matched: break
            

class Miner:
    """
    Miner class extracts useful entities, such as product.

    Miner class typically need to be customized. the generic version
    doesn't really do much. It should always be sub-classed

    """
    def __init__(self, logger):
        self._logger = logger

    def extract(self, page):
        """
        extract entities from 'page'. return a list of entities. Each
        entity is a dictionary.

        The default implementation only output the url of the page
        """
        return [ {"url": page.url,}, ]



class TaskQueue:
    """
    Holding the task for the Worker. 
    """
    def __init__(self, logger):
        self._logger = logger

    def get(self):
        """
        return the JSON string description of next task
        """
        raise Exception("Implement me")

    def put(self, task_desc_str):
        """
        append the JSON string description of the task
        """
        raise Exception("implement me")

    def size(self):
        """
        return the number of items in the queue
        """
        raise Exception("Implement me")

    def empty(self):
        """
        return true if the queue is empty
        """
        raise Exception("Implement me")

    def processed_cnt(self):
        return 0


class MemTaskQueue(TaskQueue):
    """
    Memory based task queue. For single process crawler
    """

    def __init__(self, logger):
        TaskQueue.__init__(self, logger)
        self._queue = Queue.Queue()
        self.__processed_cnt = 0

    def get(self):
        try:
            task = self._queue.get_nowait()
            if task:
                self.__processed_cnt += 1
            return task
        except Queue.Empty:
            return None

    def put(self, task_desc_str):
        try:
            self._queue.put_nowait(task_desc_str)
            return True
        except Queue.Full:
            log._logger.warn("Queue is full")
            return False

    def size(self):
        return self._queue.qsize()

    def empty(self):
        return self._queue.empty()

    def processed_cnt(self):
        return self.__processed_cnt

class DBTaskQueue(TaskQueue, SqliteHelper):
    """
    Holding the task for the Worker. 
    """
    def __init__(self, logger, name):
        TaskQueue.__init__(self, logger)
        SqliteHelper.__init__(self, name)
        self.__lock = threading.RLock()
        self.__processed_cnt = 0
        conn = self._get_conn()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                task_desc_str TEXT NOT NULL
            )
            """)

        self.__size = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]

    def get(self):
        """
        return the JSON string description of next task
        """
        task_desc_str = None
        conn = self._get_conn()
        self.__lock.acquire()
        try:
            row = conn.execute("SELECT ROWID, task_desc_str FROM tasks ORDER BY ROWID LIMIT 1").fetchone()
            if row:
                task_desc_str = row[1]
                conn.execute("DELETE FROM tasks WHERE ROWID = ?", (row[0],))
                conn.commit()
                self.__size -= 1
                self.__processed_cnt += 1
        finally:
            self.__lock.release()

        return task_desc_str

    def put(self, task_desc_str):
        """
        append the JSON string description of the task
        """
        conn = self._get_conn()
        self.__lock.acquire()
        try:
            conn.execute("INSERT INTO tasks(task_desc_str) VALUES (?)", (task_desc_str,))
            conn.commit()
            self.__size += 1
        finally:
            self.__lock.release()


    def size(self):
        """
        return the number of items in the queue
        """
        return self.__size

    def empty(self):
        """
        return true if the queue is empty
        """
        return self.size() == 0

    def processed_cnt(self):
        return self.__processed_cnt

class Worker:
    """
    do task when there are. The task is described as JSON string in 
    following format:

    {
        "url": url, 
        "revisit_interval": revisit_interval,
        "fetcher": next_fetcher,
        "seekers": next_seekers,
        "miners": next_miners,
        "hop": hop}
    }
    """
    def __init__(self, task_queue, linkdb, output, fetcher_factory, seeker_factory, miner_factory, logger, max_crawler_failed_cnt=3, max_crawler_timeout=30, crawler_retry_interval=10, pause_on_reinject=0.1, pause_before_fetch=0, pause_when_notask=0.1):
        self._running = False
        self._task_queue = task_queue
        self._linkdb = linkdb
        self._output = output
        self._fetcher_factory = fetcher_factory
        self._seeker_factory = seeker_factory
        self._miner_factory = miner_factory
        self._logger = logger

        self._max_crawler_failed_cnt = max_crawler_failed_cnt
        self._max_crawler_timeout = max_crawler_timeout
        self._crawler_retry_interval = crawler_retry_interval
        self._pause_on_reinject = pause_on_reinject
        self._pause_before_fetch = pause_before_fetch
        self._pause_when_notask = pause_when_notask

    def stop(self):
        """
        signal it to stop
        """
        self._running = False 

    def is_running(self):
        return self._running

    def run(self):
        """
        work until there no more tasks left
        """
        if self._running: return

        self._running = True

        self._logger.info("Worker started")

        try:
            while self._running:
                try:
                    self._work()
                except Exception as error:
                    self._logger.exception("Errors in Worker: %s", error)
                    time.sleep(1)
                except:
                    self._logger.error("Unknown error, sleep 1 second then continue")
                    time.sleep(1)
        finally:
            self._running = False

        self._logger.info("Worker ended")


    def _work(self):
        task_desc_str = self._task_queue.get()
        if not task_desc_str: 
            time.sleep(self._pause_when_notask)
            return

        self._logger.debug("received_new task: %s", task_desc_str)

        task_desc = json.loads(task_desc_str)

        url = task_desc['url']
        curr_hop = task_desc['hop']
        revisit_interval = task_desc['revisit_interval']

        fetcher_type = task_desc['fetcher']
        if not fetcher_type:
            self._logger.warn("Somthing is wrong. There is no 'fetcher_type' in the task description: %s", fetcher_type)
            return

        fetcher = self._fetcher_factory.get_handler(fetcher_type)

        seconds_to_pause = 0
        self._linkdb.lock()
        try:
            now = time.time()
            (last_start_ts, last_end_ts, status_code, failed_cnt)  = self._linkdb.get_status(url)
            if failed_cnt > self._max_crawler_failed_cnt: return
            if not last_start_ts: 
                # new link, start right away
                self._linkdb.mark_started(url)
            else:
                if not status_code:
                    if last_end_ts:
                        #successed before check whether need to revisit
                        if revisit_interval and now - last_end_ts > revisit_interval:
                            # prepare to revisit
                            self._linkdb.mark_started(url)
                        else:
                            return
                    else:
                        #might still crawling
                        if now - last_start_ts > self._max_crawler_timeout:
                            #consider it time out, mark that start
                            self._linkdb.mark_started(url)
                        else:
                            #probably still working on it
                            #put it back on the stack
                            self._task_queue.put(task_desc_str)
                            time.sleep(self._pause_on_reinject)
                            return
                else:
                    # failed before, waiting for retry
                    time_to_retry = (2 ** failed_cnt) * self._crawler_retry_interval + last_end_ts
                    if now > time_to_retry:
                        # time to rety
                        self._linkdb.mark_started(url)
                    else:
                        # wait for next opportunity
                        self._task_queue.put(task_desc_str)
                        time.sleep(self._pause_on_reinject)
                        return
                            
        finally:
            self._linkdb.unlock()


        # simple rate control
        if self._pause_before_fetch:
            time.sleep(self._pause_before_fetch)

        status_code = ""
        page = None
        try:
            try:
                (status_code, page) = fetcher.fetch(url);
            except:
                status_code = "Uexpected ERROR"
        finally:
            self._linkdb.lock()
            try:
                self._linkdb.mark_ended(url, status_code)
            finally:
                self._linkdb.unlock()

        if not page: 
            self._logger.info("empty page: %s", url)
            return

        new_tasks = []
        seekers = task_desc["seekers"]
        if seekers:
            for seeker_type in seekers:
                seeker = self._seeker_factory.get_handler(seeker_type)
                if seeker:
                    new_tasks += seeker.inspect(page, curr_hop)

        new_objs = []
        miners = task_desc['miners']
        if miners:
            for miner_type in miners:
                miner = self._miner_factory.get_handler(miner_type)
                if miner:
                    new_objs += miner.extract(page)
                    
        # output object
        for obj in new_objs:
            self._output.write(obj)

        self._output.flush()

        # push task instruction for next step
        for t in new_tasks:
            task_str = json.dumps(t)
            self._task_queue.put(task_str)
            self._logger.debug("push new tasks: %s", task_str)


def init_handler_from_rule(handler_rule, base_class, logger=None):
    class_name = handler_rule['class_name']
    params = handler_rule['params']
    the_class = get_class_by_name(class_name, base_class)
    if logger:
        params['logger'] = logger
    the_handler = the_class(**params)
    return the_handler

class HandlerFactory:
    """
    Create object based on name
        
    The format of the TaskRunnerFactory rules are:

    {
        "handler_type": {
                "class_name": "the name of the class",
                "params": { init parameter dictionary },
            },
    }
    """
    def __init__(self, rules, logger, base_class):
        self._logger = logger
        self._rules = rules
        self._base_class = base_class
        self._cache = {}

    def get_handler(self, handler_type):
        """
        return a task runner based for the given task_type
        """
        if not self._rules.has_key(handler_type):
            raise InvalidRulesException("The given handler_type '%s' is not coverted by the pre-configured rules", handler_type)

        if self._cache.has_key(handler_type):
            return self._cache[handler_type]

        handler_rule = self._rules[handler_type]
        the_handler = init_handler_from_rule(handler_rule, self._base_class, self._logger)
        self._cache[handler_type] = the_handler
        return the_handler

class SeekerFactory(HandlerFactory):
    """
    Create Seeker instances
    """
    def __init__(self, rules, logger):
        HandlerFactory.__init__(self, rules, logger, Seeker)

class MinerFactory(HandlerFactory):
    """
    Create Miner instances
    """
    def __init__(self, rules, logger):
        HandlerFactory.__init__(self, rules, logger, Miner)


class FetcherFactory(HandlerFactory):
    """
    Create task running instances
    """
    def __init__(self, rules, logger):
        HandlerFactory.__init__(self, rules, logger, Fetcher)


class Job:
    """
    define the whole crawler job
    """
    def __init__(self, job_rules, logger):
        self._job_rules = job_rules
        self._worker_params = self._job_rules['worker_params']
        if logger:
            self._logger = logger
        else:
            self._logger = init_logger(self._job_rules['name'])
        self._task_queue = init_handler_from_rule(self._job_rules['task_queue'], TaskQueue, self._logger)
        self._linkdb = init_handler_from_rule(self._job_rules['linkdb'], LinkDB, self._logger)
        self._output = init_handler_from_rule(self._job_rules['output'], Output, self._logger)
        self._init_fetcher_factory()
        self._init_seeker_factory()
        self._init_miner_factory()
        self.__workers = []
        self.__threads = []
        self.__running = False

    def _init_fetcher_factory(self):
        self._fetcher_factory = FetcherFactory(self._job_rules['fetcher_factory']['rules'], self._logger)

    def _init_seeker_factory(self):
        self._seeker_factory = SeekerFactory(self._job_rules['seeker_factory']['rules'], self._logger)

    def _init_miner_factory(self):
        self._miner_factory = MinerFactory(self._job_rules['miner_factory']['rules'], self._logger)

    def start(self):
        if self.__running: return
        self.__running = True

        for t in self._job_rules['seed_tasks']:
            self._task_queue.put(json.dumps(t))

        for i in range(self._job_rules['num_workers']):
            worker = Worker(
                self._task_queue,
                self._linkdb,
                self._output,
                self._fetcher_factory,
                self._seeker_factory,
                self._miner_factory,
                self._logger,
                **self._worker_params)

            thread = threading.Thread(target=worker.run, name="worker %s" % (i,) )
            thread.start()

            self.__workers.append(worker)
            self.__threads.append(thread)

    def is_running(self):
        if not self.__running: return False
        if not self._task_queue.empty(): return True 
        for t in self.__threads:
            if t.is_alive(): return True

        return False

    def is_idle(self):
        return self._task_queue.empty()


    def stop(self, timeout=None):
        for w in self.__workers:
            w.stop()

        for t in self.__threads:
            t.join(timeout)

        self._output.close()

        self.__running = False
            

    def status(self):
        return "Workers: %s, Tasks:(%s, pending:%s), Links:(%s, succ:%s, fail:%s), Output: %s" % (
                len(self.__workers),
                self._task_queue.processed_cnt(),
                self._task_queue.size(),
                self._linkdb.started_cnt(),
                self._linkdb.succeeded_cnt(),
                self._linkdb.failed_cnt(),
                self._output.count(),
                )

        
def run_job(job_rules, max_idle_cnt=10, job_status_interval=1, logger=None):
    """
    Convenience wrapper for running a crawling job
    """
    if not job_rules:
        raise Exception("job_rules was not provided")

    if logger is None:
        logger = bee.init_logger("run_job")

    job = Job(job_rules=job_rules, logger=logger)

    logger.info("Starting up the crawling job")
    job.start()

    logger.info("Waiting job to be done")
    idle_cnt = 0
    while job.is_running():
        try:
            logger.info("idle_cnt: %s, %s", idle_cnt, job.status())
            if job.is_idle():
                idle_cnt += 1
                if idle_cnt >= max_idle_cnt:
                    logger.info("idle_cnt %s reached max, prepare to stop", idle_cnt)
                    break
            else:
                idle_cnt = 0

            time.sleep(job_status_interval)
        except:
            logger.exception("Errors in job loop")
            break

    logger.info("preparing to stop job")
    job.stop()
            
    logger.info("Job is done")


def test_miner(logger, miner_class_name, url, from_encoding):
    """
    Simple miner tester
    """
    fetcher = SimpleHTTPFetcher(logger, from_encoding=from_encoding)
    (status_code, page) = fetcher.fetch(url)

    miner_class = get_class_by_name(miner_class_name, Miner)
    miner = miner_class(logger)
    prods = miner.extract(page)

    for prod in prods:
        print json.dumps(prod, indent=4, ensure_ascii=False, sort_keys=True)

def test_seeker(logger, seeker_class_name, url, **kwarg):
    fetcher = SimpleHTTPFetcher(logger)
    (status_code, page) = fetcher.fetch(url)

    seeker_class = get_class_by_name(seeker_class_name, Seeker) 
    seeker = seeker_class(logger, **kwarg)

    new_tasks = seeker.inspect(page, 0)

    print json.dumps(new_tasks, indent=4)
 
