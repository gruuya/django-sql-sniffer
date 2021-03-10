import argparse
import signal
import time
import threading
from multiprocessing.connection import Listener
from django_sql_sniffer import analyzer, injector, sniffer


class DjangoSQLListener(threading.Thread):
    def __init__(self, cmdline_args):
        super().__init__(name=self.__class__.__name__)
        self.analyzer = analyzer.SQLAnalyzer(tail=cmdline_args.tail, top=cmdline_args.number, by_sum=cmdline_args.sum, by_count=cmdline_args.count)
        self.logger = sniffer.configure_logger(__name__, cmdline_args.verbose)
        self._target_pid = cmdline_args.pid
        self._verbose = cmdline_args.verbose
        self._listener = None
        self._conn = None
        self._running = False

    def _create_socket(self):
        self._listener = Listener(('localhost', 0))  # will force OS to assign a random available port
        _, self.port = self._listener.address
        self.logger.debug(f"listening on port {self.port}")

    def _inject_sniffer(self):
        with open(sniffer.__file__, "r") as source_file:
            source_code = source_file.read()
            code_to_inject = source_code.replace("PORT = 0", f"PORT = {self.port}")
            code_to_inject = code_to_inject.replace("LOGGING_ENABLED = False", f"LOGGING_ENABLED = {self._verbose}")
            code_to_inject += "sniffer.start()"
        injector.inject(str(self._target_pid), code_to_inject, self._verbose)
        self.logger.debug("SQL sniffer injected, waiting for a reply")

    def _callback_wait(self):
        self._conn = self._listener.accept()
        self._listener.close()
        self.logger.debug("reply received, sniffer active")

    def start(self):
        self.logger.debug("starting")
        self._create_socket()
        self._inject_sniffer()
        self._callback_wait()
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
                    self.analyzer.record_query(sql, duration)
            except EOFError:
                self.logger.info("sniffer disconnected, exiting")
                self._running = False
            except Exception as e:
                self.logger.error(f"unexpected error: {str(e)}", exc_info=True)
                self._running = False

        self.analyzer.print_summary()
        self._conn.close()
        injector.inject(str(self._target_pid), "sniffer.stop()", self._verbose)
        self.logger.debug("done")


def main():
    parser = argparse.ArgumentParser(description="Analyze SQL queries originating from a running process")
    parser.add_argument("-p", "--pid", help="The id of the process executing Django SQL queries")
    parser.add_argument("-t", "--tail", action='store_true', help="Log queries as they are executed in tail mode")
    parser.add_argument("-v", "--verbose", action='store_true', help="Verbose mode - enables non-SQL logging on server and client (injected) side")
    parser.add_argument("-s", "--sum", action='store_true', help="Sort query summary by total combined time")
    parser.add_argument("-c", "--count", action='store_true', help="Sort query summary by execution count")
    parser.add_argument("-n", "--number", type=int, default=3, help="Number of top queries and their stats to display in summary")
    args = parser.parse_args()

    listener = DjangoSQLListener(args)
    listener.start()
    signal.signal(signal.SIGTERM, listener.stop)
    signal.signal(signal.SIGINT, listener.stop)
    if hasattr(signal, "SIGINFO"):
        signal.signal(signal.SIGINFO, listener.analyzer.print_summary)  # print summary on ^T, without exiting the process
    while listener.is_alive():
        time.sleep(1)


if __name__ == "__main__":
    main()
