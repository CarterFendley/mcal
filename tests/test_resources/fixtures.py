import os
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import pytest


@dataclass
class ExecutableSpec:
    return_code: int = 0
    echo: str = None
    echo_stderr: str = None

@pytest.fixture
def with_executable(tmp_path_factory) -> Callable[[], str]:
    def _with_executable(
        spec: ExecutableSpec = None
    ) -> str:
        """
        Function to generate a executable with characteristics specified by a specification.

        Args:
            spec (ExecutableSpec, optional): The specification to build an executable from. Defaults to None.

        Returns:
            str: The absolute path to the executable
        """
        if spec is None:
            spec = ExecutableSpec()

        exe_path: Path = tmp_path_factory.mktemp("with_executable") / "executable.sh"

        with open(exe_path, 'w') as f:
            f.write("#!/usr/bin/env bash\n")
            if spec.echo is not None:
                f.write(f"echo \"{spec.echo}\"\n")
            if spec.echo_stderr is not None:
                f.write(f">&2 echo \"{spec.echo_stderr}\"\n")
            f.write(f"exit {spec.return_code}")

        # Make executable
        os.chmod(
            exe_path,
            os.stat(exe_path).st_mode | stat.S_IXUSR
        )
        return str(exe_path)

    return _with_executable