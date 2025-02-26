import os
import re
from pathlib import Path

from test_resources.cli_fixtures import CLIRunFixture

THIS_DIR = os.path.abspath(os.path.dirname(__file__))
CONFIG_DUMMY_WATCHER = os.path.join(THIS_DIR, 'config_dummy_watcher.yml')

def test_watcher(cli_run: CLIRunFixture, tmpdir: Path):
    result, _ = cli_run(
        CONFIG_DUMMY_WATCHER,
        config_arguments={},
        run_cmd_kwargs={
            'capture_output': True
        }
    )

    stdout = result.stdout.decode()
    for i in range(5):
        assert re.search(fr"Watcher found sample number: {i}\n", stdout) is not None, f"Regex failed: {stdout}"