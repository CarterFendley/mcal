from pathlib import Path

import jinja2
import oyaml as yaml
import pydantic
import pytest
from test_resources.configs import *

from mcal.config import MCalConfig, load_config_file


@pytest.mark.parametrize(
    "path, error_type",
    [
        (BAD_NOT_YAML, AssertionError),
        (BAD_NOT_CONFIG, pydantic.ValidationError),
        (BAD_INVALID_SAMPLER, pydantic.ValidationError),
        (BAD_INVALID_SCHEDULE, pydantic.ValidationError),
        (BAD_INVALID_STOP_ONE, pydantic.ValidationError),
        (BAD_INVALID_STOP_TWO, pydantic.ValidationError),
        (BAD_INVALID_STOP_THREE, pydantic.ValidationError),
        (BAD_INVALID_STOP_FOUR, pydantic.ValidationError),
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
    assert isinstance(config, MCalConfig)

def test_save_config(tmpdir: Path):
    input_config = load_config_file(COMPLETE_CONFIG, {})

    exists_path = Path(tmpdir) / 'file_exists.yml'
    exists_path.touch()
    with pytest.raises(AssertionError):
        input_config.save(exists_path)
    
    save_path = tmpdir / 'save_file'
    input_config.save(save_path)

    output_config = load_config_file(save_path, {})
    assert input_config.model_dump() == output_config.model_dump()