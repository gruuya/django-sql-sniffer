import time
import threading
import queue
import signal
from multiprocessing.connection import Client
try:
    from django.db.backends.utils import CursorWrapper  # django >= 1.7.x
except ImportError:
    from django.db.backends.util import CursorWrapper  # django <= 1.6.x


_original_execute = CursorWrapper.execute
_original_executemany = CursorWrapper.executemany
PORT = 0
LOGGING_ENABLED = False


def log(message):
    if LOGGING_ENABLED:
        print(message)


class DjangoSQLSniffer(threading.Thread):

    def __init__(self):
        self._conn = None
        self._running = False
        super().__init__(name=self.__class__.__name__)

    def monkey_patch_django_sql_sniffer(self):
        log(f"[{self.__class__.__name__}] Monkey patching Django SQL Cursor Wrapper")

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
        log(f"[{self.__class__.__name__}] Rolling back Django SQL Cursor Wrapper monkey patch")

        CursorWrapper.execute = _original_execute
        CursorWrapper.executemany = _original_executemany

    def start(self):
        log(f"[{self.__class__.__name__}] Starting")
        self.monkey_patch_django_sql_sniffer()
        self._conn = Client(('localhost', PORT))
        self._running = True
        super().start()

    def stop(self, *a, **kw):
        self._running = False

    def run(self):
        log(f"[{self.__class__.__name__}] Started")
        while self._running:
            try:
                sql, duration = executed_sql.get(timeout=5)
                log(f"[{self.__class__.__name__}] Streaming SQL {sql}")
                sql_packet = dict(
                    sql=sql,
                    duration=duration
                )

                self._conn.send(sql_packet)
            except queue.Empty:
                log(f"[{self.__class__.__name__}] No SQL executions in the last 5 seconds")
            except BrokenPipeError:
                log(f"[{self.__class__.__name__}] SQL streaming socket closed, exiting")
                self._running = False
            except Exception as e:
                log(f"[{self.__class__.__name__}] Unexpected error: {str(e)}")
                self._running = False

        self._conn.close()
        self.rollback_django_sql_sniffer()
        log(f"[{self.__class__.__name__}] Done")


executed_sql = queue.Queue()
sniffer = DjangoSQLSniffer()
signal.signal(signal.SIGTERM, sniffer.stop)
signal.signal(signal.SIGINT, sniffer.stop)
