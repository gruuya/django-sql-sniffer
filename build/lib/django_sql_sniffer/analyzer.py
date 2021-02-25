import threading
try:
    import sqlparse
except ImportError:
    sqlparse = None
from django_sql_sniffer import sniffer, version


SQL_STATS_TEXT = """
  ____    ___   _       ____  _____   _   _____  ____  
 / ___|  / _ \ | |     / ___||_   _| / \ |_   _|/ ___| 
 \___ \ | | | || |     \___ \  | |  / _ \  | |  \___ \ 
  ___) || |_| || |___   ___) | | | / ___ \ | |   ___) |
 |____/  \__\_\|_____| |____/  |_|/_/   \_\|_|  |____/ 
"""
DELIMETER_LENGTH = 55


def format_sql(sql):
    if sqlparse is not None:
        return sqlparse.format(sql, reindent_aligned=True)
    return sql


def format_duration(duration):
    return "{0:0.9f}".format(duration)


class SQLAnalyzer(threading.Thread):
    def __init__(self, conn, verbose=False, tail=False, top=3, by_sum=False, by_count=False):
        super().__init__(name=self.__class__.__name__)
        self._conn = conn
        self._executed_queries = dict()
        self._tail = tail
        self._top = top
        self._by_sum = by_sum
        self._by_count = by_count
        self._running = False
        self.logger = sniffer.configure_logger(__name__, verbose)

    def record_query(self, sql, duration):
        if sql in self._executed_queries:
            self._executed_queries[sql]["count"] += 1
            self._executed_queries[sql]["max"] = max(duration, self._executed_queries[sql]["max"])
            self._executed_queries[sql]["sum"] += duration
        else:
            self._executed_queries[sql] = dict(
                count=1,
                max=duration,
                sum=duration
            )

    def print_query(self, sql, duration):
        stats = self._executed_queries[sql]
        print("Count: ", stats["count"], "; Duration: ", format_duration(duration), "; Max Duration: ", format_duration(stats["max"]), "; Query:", sep="")
        print(format_sql(sql))
        print("-" * DELIMETER_LENGTH)

    def print_summary(self, *a, **kw):
        sort_field = "count" if self._by_count else "sum" if self._by_sum else "max"
        sorted_queries = sorted(self._executed_queries.items(), key=lambda x: x[1][sort_field], reverse=True)

        print("\n\n" + "=" * DELIMETER_LENGTH)
        print(SQL_STATS_TEXT)
        print(f"Django SQL Sniffer v{version}".center(DELIMETER_LENGTH))
        print("=" * DELIMETER_LENGTH)
        print(f"TOP QUERIES BY {'COUNT' if self._by_count else 'COMBINED DURATION' if self._by_sum else 'MAX DURATION'}\n\n".center(DELIMETER_LENGTH))
        for sql, stats in sorted_queries[:self._top]:
            print("Count: ", stats["count"], "; Max Duration: ", format_duration(stats["max"]), "; Combined Duration: ", format_duration(stats["sum"]), "; Query:", sep="")
            print(format_sql(sql))
            print("-" * DELIMETER_LENGTH)
        print("=" * DELIMETER_LENGTH)

    def start(self):
        self.logger.debug("starting")
        self._running = True
        super().start()

    def stop(self, *a, **kw):
        self.logger.debug("stopping")
        self._running = False

    def run(self):
        while self._running:
            try:
                if self._conn.poll(3):
                    sql_packet = self._conn.recv()
                    duration = sql_packet["duration"]
                    sql = sql_packet["sql"]
                    self.record_query(sql, duration)
                    if self._tail:
                        self.print_query(sql, duration)
            except EOFError:
                self.logger.info("sniffer disconnected, exiting")
                self._running = False
            except Exception as e:
                self.logger.error(f"unexpected error: {str(e)}", exc_info=True)
                self._running = False

        self._conn.close()
        self.logger.debug("done")
