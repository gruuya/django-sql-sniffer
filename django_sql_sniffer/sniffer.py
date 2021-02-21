import time
import threading
import queue
import signal
import logging
import django.db.backends.utils  # django >= 1.7.x
from multiprocessing.connection import Client


logger = logging.getLogger(__name__)


_originalCursorWrapper = django.db.backends.utils.CursorWrapper
PORT = 0
LOGGING_ENABLED = False
if not LOGGING_ENABLED:
    logger.addHandler(logging.NullHandler())
else:
    logger.setLevel(logging.DEBUG)


class DjangoSQLSnifferWrapper(django.db.backends.utils.CursorWrapper):

    def execute(self, sql, params=None):
        t0 = time.time()
        try:
            return super().execute(sql, params=params)
        finally:
            duration = t0 - time.time()
            executed_sql.put((sql, duration))

    def executemany(self, sql, param_list):
        t0 = time.time()
        try:
            return super().executemany(sql, param_list=param_list)
        finally:
            duration = t0 - time.time()
            executed_sql.put((sql, duration))


class DjangoSQLSnifferStreamer(threading.Thread):

    def __init__(self):
        self._conn = None
        self._running = False
        super().__init__(name=self.__class__.__name__)

    def monkey_patch_django_sql_sniffer(self):
        logger.debug("[%s] Monkey patching Django SQL Cursor Wrapper", self.__class__.__name__)
        django.db.backends.utils.CursorWrapper = DjangoSQLSnifferWrapper

    def rollback_django_sql_sniffer(self):
        logger.debug("[%s] Rolling back Django SQL Cursor Wrapper monkey patch", self.__class__.__name__)
        django.db.backends.utils.CursorWrapper = _originalCursorWrapper

    def start(self):
        logger.debug("[%s] Starting", self.__class__.__name__)
        self.monkey_patch_django_sql_sniffer()
        self._conn = Client(('localhost', PORT))
        self._running = True
        super().start()

    def stop(self, *a, **kw):
        self._running = False

    def run(self):
        logger.debug("[%s] Started", self.__class__.__name__)
        while self._running:
            try:
                sql, duration = executed_sql.get(timeout=5)
                logger.debug("[%s] Streaming SQL %s", self.__class__.__name__, sql)
                sql_packet = dict(
                    sql=sql,
                    duration=duration
                )

                self._conn.send(sql_packet)
            except queue.Empty:
                logger.debug("[%s] No SQL executions in the last 5 seconds", self.__class__.__name__)
            except BrokenPipeError:
                logger.warning("[%s] SQL streaming socket closed, exiting", self.__class__.__name__)
                self._running = False
            except Exception:
                logger.error("[%s] Unexpected error", self.__class__.__name__, exc_info=True)
                self._running = False

        self._conn.close()
        self.rollback_django_sql_sniffer()
        logger.debug("[%s] Done", self.__class__.__name__)


executed_sql = queue.Queue()
streamer_thread = DjangoSQLSnifferStreamer()
signal.signal(signal.SIGTERM, streamer_thread.stop)
signal.signal(signal.SIGINT, streamer_thread.stop)
