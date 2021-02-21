import argparse
import signal
from multiprocessing.connection import Listener
from django_sql_sniffer import analyzer, injector, sniffer


def main():
    # parse arguments
    parser = argparse.ArgumentParser(description="Analyze SQL queries originating from a running process.")
    parser.add_argument("-p", "--pid", help="The id of the process executing Django SQL queries.")
    parser.add_argument("-v", "--verbose", action='store_true', help="Verbose mode - enables non-SQL logging on server and client (injected) side.")
    parser.add_argument("-t", "--tail", action='store_true', help="Log SQL queries as they are executed in tail mode.")
    args = parser.parse_args()

    # create socket and listen for a connection
    listener = Listener(('localhost', 0))  # will force OS to assign a random available port
    _, port = listener.address
    print(f"[{__file__}] listening on port {port}")

    # inject sniffer monkey patch
    with open(sniffer.__file__, "r") as source_file:
        source_code = source_file.read()
        code_to_inject = source_code.replace("PORT = 0", f"PORT = {port}")
        code_to_inject = code_to_inject.replace("LOGGING_ENABLED = False", f"LOGGING_ENABLED = {args.verbose}")
        code_to_inject += "streamer_thread.start()"
    injector.inject(str(args.pid), code_to_inject, args.verbose)

    # wait for callback
    print(f"[{__file__}] SQL sniffer injected, waiting for a reply")
    conn = listener.accept()

    # receive packets and decode
    print(f"[{__file__}] reply received, sniffing")
    sql_analyzer = analyzer.SQLQueryAnalyzer()
    signal.signal(signal.SIGINT, sql_analyzer.print_summary)
    while True:
        try:
            sql_packet = conn.recv()
            duration = sql_packet["duration"]
            sql = sql_packet["sql"]
            sql_analyzer.record_query(sql, duration)
            if args.tail:
                print(f"[{__file__}] Duration: {duration}, SQL:\n{sql}")
        except EOFError:
            print(f"[{__file__}] sniffer disconnected")
            break
        except Exception as e:
            print(f"[{__file__}] error: {str(e)}")
            break

    conn.close()
    listener.close()


if __name__ == "__main__":
    main()
