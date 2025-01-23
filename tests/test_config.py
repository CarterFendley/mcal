import jinja2
import pydantic
import pytest
from test_resources.configs import *

from k_calibrate.config import KCConfig, load_config_file


@pytest.mark.parametrize(
    "path, error_type",
    [
        (BAD_NOT_YAML, AssertionError),
        (BAD_NOT_CONFIG, pydantic.ValidationError),
        (BAD_INVALID_SAMPLER, pydantic.ValidationError),
        (BAD_INVALID_SCHEDULE, pydantic.ValidationError),
        (WITH_ARGUMENTS, jinja2.UndefinedError),
    ]
)
def test_bad_configs(path: str, error_type):
    with pytest.raises(error_type):
        load_config_file(path, {})

@pytest.mark.parametrize(
    "path, args",
    [
        (COMPLETE_CONFIG, {}),
        (WITH_ARGUMENTS, {'time': 'my time'})
    ]
)
def test_good_config(path: str, args: dict):
    config = load_config_file(path, args)
    assert isinstance(config, KCConfig)