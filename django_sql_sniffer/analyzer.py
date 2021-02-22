import threading
try:
    import sqlparse
except ImportError:
    sqlparse = None


def format_sql(sql):
    if sqlparse is not None:
        return sqlparse.format(sql, reindent_aligned=True)
    return sql


class SQLQueryAnalyzer(threading.Thread):
    def __init__(self, conn, tail=False, top=5, by_total=False, by_count=False):
        super().__init__(name=self.__class__.__name__)
        self._conn = conn
        self._executed_queries = dict()
        self._tail = tail
        self._top = top
        self._by_total = by_total
        self._by_count = by_count
        self._running = False

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

    def print_summary(self):
        sort_field = "count" if self._by_count else "total" if self._by_total else "max"
        sorted_queries = sorted(self._executed_queries.items(), key=lambda x: x[1][sort_field])

        print("**************************    SQL EXECUTION SUMMARY    **************************")
        for sql, stats in sorted_queries[:self._top]:
            print("Count: ", stats["count"], "; Max Duration: ", stats["max"], "; Total Duration ", stats["total"], "; Query:")
            print(format_sql(sql))
            print("-" * 80)
        print("=" * 80)

    def start(self):
        self._running = True
        super().start()

    def run(self):
        while self._running:
            try:
                sql_packet = self._conn.recv()
                duration = sql_packet["duration"]
                sql = sql_packet["sql"]
                self.record_query(sql, duration)
                if self._tail:
                    self.print_query(sql, duration)
            except EOFError:
                print(f"[{self.__class__.__name__}] sniffer disconnected")
                self._running = False
            except Exception as e:
                print(f"[{self.__class__.__name__}] error: {str(e)}")
                self._running = False

        self._conn.close()

    def stop(self, *a, **kw):
        self._running = False
