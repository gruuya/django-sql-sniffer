class SQLQueryAnalyzer:
    def __init__(self, top=5, by_total=False, by_count=False):
        self._executed_queries = dict()
        self._top = top
        self._by_total = by_total
        self._by_count = by_count

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

    def print_summary(self, *a, **kw):
        sort_field = "count" if self._by_count else "total" if self._by_total else "max"
        sorted_queries = sorted(self._executed_queries.items(), key=lambda x: x[1][sort_field])
        print(sorted_queries[:self._top])
