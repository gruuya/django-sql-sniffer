import os
import subprocess
import tempfile
from django_sql_sniffer import sniffer


def inject(pid, code_to_inject, verbose=True):
    logger = sniffer.configure_logger(__name__, verbose)

    with tempfile.NamedTemporaryFile(mode="r+") as temp_file:
        temp_file.write(code_to_inject)
        temp_file.flush()

        if os.uname()[0] == 'Darwin':
            args = [
                "--one-line 'expr void* $gil=(void *) PyGILState_Ensure()'",
                f"--one-line 'expr (void) PyRun_SimpleString(\"exec(open(\\\"{temp_file.name}\\\").read())\")'",
                "--one-line 'expr (void) PyGILState_Release($gil)'"
            ]
            command = ["lldb", "-p", pid, "-b"] + args
        else:
            args = [
                "-eval-command='call PyGILState_Ensure()'",
                f"-eval-command='call PyRun_SimpleString(\"exec(open(\\\"{temp_file.name}\\\").read())\")'",
                "-eval-command='call PyGILState_Release($1)'"
            ]
            command = ["gdb", "-p", pid, "-batch"] + args

        final_command = " ".join(command)
        res = subprocess.run(final_command, capture_output=True, check=True, shell=True)

    logger.debug(f"injected command resulted in return code {res.returncode} with output:\n{res.stdout}")
    if res.stderr != b"":
        logger.error(f"injected command resulted in error:\n{res.stderr}")


# for debugging purposes
if __name__ == "__main__":
    import sys
    inject(sys.argv[1], sys.argv[2])
