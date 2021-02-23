import time
import threading
import queue
import logging
import sys
from multiprocessing.connection import Client
try:
    from django.db.backends.utils import CursorWrapper  # django >= 1.7.x
except ImportError:
    from django.db.backends.util import CursorWrapper  # django <= 1.6.x


_original_execute = CursorWrapper.execute
_original_executemany = CursorWrapper.executemany
PORT = 0
LOGGING_ENABLED = False


def configure_logger(name, enabled=False):
    logger = logging.Logger(name, logging.DEBUG)
    if not enabled:
        logger.addHandler(logging.NullHandler())
    else:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(f"%(asctime)s %(levelname)s | [{logger.name}] %(message)s"))
        handler.setLevel(logging.DEBUG)
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
    return logger


class DjangoSQLSniffer(threading.Thread):

    def __init__(self):
        self._conn = None
        self._running = False
        self.logger = configure_logger("django_sql_sniffer", LOGGING_ENABLED)
        super().__init__(name=self.__class__.__name__, daemon=True)

    def monkey_patch_django_sql_sniffer(self):
        self.logger.debug("monkey patching Django SQL Cursor Wrapper")

        def execute(self, sql, params=None):
            t0 = time.time()
            try:
                return _original_execute(self, sql, params=params)
            finally:
                duration = time.time() - t0
                executed_sql.put((sql, duration))

        def executemany(self, sql, param_list):
            t0 = time.time()
            try:
                return _original_executemany(self, sql, param_list=param_list)
            finally:
                duration = time.time() - t0
                executed_sql.put((sql, duration))

        CursorWrapper.execute = execute
        CursorWrapper.executemany = executemany

    def rollback_django_sql_sniffer(self):
        self.logger.debug("rolling back Django SQL Cursor Wrapper monkey patch")

        CursorWrapper.execute = _original_execute
        CursorWrapper.executemany = _original_executemany

    def start(self):
        self.logger.debug("starting")
        self.monkey_patch_django_sql_sniffer()
        self._conn = Client(('localhost', PORT))
        self._running = True
        super().start()

    def stop(self, *a, **kw):
        self.logger.debug("stopping")
        self._running = False

    def run(self):
        self.logger.debug("started")
        while self._running:
            try:
                sql, duration = executed_sql.get(timeout=5)
                self.logger.debug(f"streaming SQL {sql}")
                sql_packet = dict(
                    sql=sql,
                    duration=duration
                )

                self._conn.send(sql_packet)
            except queue.Empty:
                self.logger.debug("no SQL executions in the last 5 seconds")
            except BrokenPipeError:
                self.logger.info("streaming socket closed, exiting")
                self._running = False
            except Exception as e:
                self.logger.warning(f"unexpected error: {str(e)}")
                self._running = False

        self._conn.close()
        self.rollback_django_sql_sniffer()
        self.logger.debug("done")


executed_sql = queue.Queue()
sniffer = DjangoSQLSniffer()
