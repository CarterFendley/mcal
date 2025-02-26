import pytest
from test_resources import ENV_BAD_FILE, ENV_FILE, ENV_FILE_EMPTY

from mcal.utils.env_file import load_env_file


def test_env_load():
    env = load_env_file(ENV_FILE)

    assert env.get_user_key() == 'XXXXX'
    assert env.get_license_key() == 'YYYYY'

def test_no_values():
    env = load_env_file(ENV_FILE_EMPTY)

    with pytest.raises(RuntimeError):
        env.get_user_key()
    with pytest.raises(RuntimeError):
        env.get_license_key()

def test_bad_file():
    with pytest.raises(RuntimeError):
        load_env_file('path/to/file/that_doesnt_exist.txt')
    with pytest.raises(RuntimeError):
        load_env_file(ENV_BAD_FILE)
