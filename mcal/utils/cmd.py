import subprocess
import sys
from typing import List


class CommandException(Exception):
    def __init__(self, msg: str, return_code: int):
        super().__init__(msg)
        self.return_code = return_code

def run_cmd(
    args: List[str],
    expected_return_codes: List[int] = (0,),
    **kwargs
) -> subprocess.CompletedProcess:
    result = subprocess.run(
        args=args,
        **kwargs
    )

    # If capture output is supplied, do stderr logging
    if kwargs.get('capture_output', False):
        std_err = result.stderr.decode()
        if std_err != '':
            print(f"stderr forwarded from '{args[0]}':", file=sys.stderr)
            print('---------------------------', file=sys.stderr)
            print(std_err, file=sys.stderr)
            print('---------------------------', file=sys.stderr)

    # Protect against unwanted error codes
    if result.returncode not in expected_return_codes:
        raise CommandException(
            msg=f"Unexpected return code '{result.returncode}' from command: '{' '.join(args)}'",
            return_code=result.returncode
        )

    return result

def is_cmd(cmd: str) -> bool:
    """
    Utility for assuring that a command is valid through use of `which`.

    Returns:
        bool: Indicating if the command was found.
    """

    result = run_cmd(
        ['which', cmd],
        expected_return_codes=(0, 1),
        stderr=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL
    )

    if result.returncode == 0:
        return True
    elif result.returncode == 1:
        return False