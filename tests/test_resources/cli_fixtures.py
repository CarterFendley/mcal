
from pathlib import Path
from subprocess import CompletedProcess
from typing import Any, Dict, Optional, Protocol, Tuple, TypeAlias

import pytest

from k_calibrate.saves import SampleRun, load_run
from k_calibrate.utils.cmd import run_cmd

CLIRunResult: TypeAlias = Tuple[CompletedProcess, Optional[SampleRun]]
class CLIRunFixture(Protocol):
    def __call__(
        self,
        config_path: str,
        config_arguments: Dict[str, str],
        run_cmd_kwargs: Optional[Dict[str, Any]] = None
    ) -> CLIRunResult:
        ...

@pytest.fixture
def cli_run(tmp_path_factory) -> CLIRunFixture:
    def _cli_run(
        config_path: str,
        config_arguments: Dict[str, str],
        run_cmd_kwargs: Optional[Dict[str, Any]] = None
    ) -> CLIRunResult:
        if run_cmd_kwargs is None:
            run_cmd_kwargs = {}

        tmp_path: Path = tmp_path_factory.mktemp("kc_run_data")
        cli_args = [
            'kc', '-vvv', 'run', config_path,
            '--save-directory', str(tmp_path),
            '--save-name', 'run_data'
        ]
        for arg_name, arg_value in config_arguments.items():
            assert isinstance(arg_value, str), "This fixture provides a CLI runner, all arguments must be in string format. Found parameter '%s' with non string type: %s" % (arg_value, type(arg_value))
            cli_args.append(f"--{arg_name}={arg_value}")

        result = run_cmd(
            args=cli_args,
            **run_cmd_kwargs
        )

        if result.returncode == 0:
            run_data_path = tmp_path / 'run_data'
            run_data = load_run(run_data_path)
        else: 
            run_data = None

        return result, run_data

    return _cli_run
