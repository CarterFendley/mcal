import os
from datetime import timedelta

import pytest
from test_resources.cli_fixtures import CLIRunFixture

THIS_DIR = os.path.abspath(os.path.dirname(__file__))
CONFIG_ONE_ACTION_NO_AWAIT = os.path.join(THIS_DIR, 'config_one_action_no_await.yml')

def test_orchestrator_shutdowns_on_error