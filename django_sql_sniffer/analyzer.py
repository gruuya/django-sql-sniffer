import threading
try:
    import sqlparse
except ImportError:
    sqlparse = None
from django_sql_sniffer import sniffer


def format_sql(sql):
    if sqlparse is not None:
        return sqlparse.format(sql, reindent_aligned=True)
    return sql


class SQLAnalyzer(threading.Thread):
    def __init__(self, conn, verbose=False, tail=False, top=3, by_total=False, by_count=False):
        super().__init__(name=self.__class__.__name__)
        self._conn = conn
        self._executed_queries = dict()
        self._tail = tail
        self._top = top
        self._by_total = by_total
        self._by_count = by_count
        self._running = False
        self.logger = sniffer.configure_logger(__name__, verbose)

    def record_query(self, sql, duration):
        if sql in self._executed_queries:
            self._executed_queries[sql]["count"] += 1
            self._executed_queries[sql]["max"] = max(duration, self._executed_queries[sql]["max"])
            self._executed_queries[sql]["total"] += duration
        else:
            self._executed_queries[sql] = dict(
                count=1,
                max=duration,
                total=duration
            )

    def print_query(self, sql, duration):
        stats = self._executed_queries[sql]
        print("Count: ", stats["count"], "; Duration: ", duration, "; Max Duration: ", stats["max"], "; Total Duration ", stats["total"], "; Query:")
        print(format_sql(sql))
        print("-" * 80)

    def print_summary(self, *a, **kw):
        sort_field = "count" if self._by_count else "total" if self._by_total else "max"
        sorted_queries = sorted(self._executed_queries.items(), key=lambda x: x[1][sort_field], reverse=True)

        print("**************************    SQL EXECUTION SUMMARY    **************************")
        for sql, stats in sorted_queries[:self._top]:
            print("Count: ", stats["count"], "; Max Duration: ", stats["max"], "; Total Duration ", stats["total"], "; Query:")
            print(format_sql(sql))
            print("-" * 80)
        print("=" * 80)

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
