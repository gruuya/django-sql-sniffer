import argparse
import time
import uuid
from multiprocessing import Process, Queue
from unittest import mock
from django_sql_sniffer import listener


def test_end_2_end():
    query_queue = Queue()

    # define dummy method which will utilize Django DB cursor in the target process
    def dummy_query_executor():
        from django.db import connection
        cursor = connection.cursor()
        while True:
            query = query_queue.get()
            try:
                cursor.execute(query)
            except Exception as e:
                pass  # there are no tables so we just pass random uuid strings for testing purposes

    # start the target process
    tp = Process(name="target_process", target=dummy_query_executor)
    tp.start()

    # start the listener thread
    with mock.patch('argparse.ArgumentParser.parse_args', return_value=argparse.Namespace(pid=tp.pid, tail=False, verbose=False, sum=False, count=False, number=3)):
        parser = argparse.ArgumentParser()
        args = parser.parse_args()
        lt = listener.DjangoSQLListener(args)
        lt.start()

    # execute dummy queries
    queries = []
    for i in range(100):
        query = str(uuid.uuid4())
        queries.append(query)
        query_queue.put(query)

    # check listener configured properly
    assert lt._target_pid == args.pid
    assert lt._verbose == args.verbose
    assert lt.analyzer._tail == args.tail
    assert lt.analyzer._top == args.number
    assert lt.analyzer._by_sum == args.sum
    assert lt.analyzer._by_count == args.count

    time.sleep(4)
    tp.kill()

    # check all queries captured
    assert set(queries) == set(lt.analyzer._executed_queries.keys())

    # check that listener shuts down once it detects the target process is not alive
    time.sleep(4)
    assert not lt.is_alive()
