import os
from dataclasses import dataclass
from typing import Any

import toml

DEFAULT_PATH='env.toml'

@dataclass
class EnvFile:
    _data: dict

    def _get(self, attribute: str) -> Any:
        if attribute not in self._data:
            raise RuntimeError(f"Env file has no entry '{attribute}'")
        return self._data[attribute]

    def get_account_id(self) -> str:
        return self._get('account_id')

    def get_user_key(self) -> str:
        return self._get('user_key')

    def get_license_key(self) -> str:
        return self._get('license_key') 

def load_env_file(path: str=DEFAULT_PATH) -> EnvFile:
    if not os.path.isfile(path):
        raise RuntimeError("Env path is not a file: %s" % path)

    try:
        return EnvFile(_data=toml.load(path))
    except toml.TomlDecodeError as err: 
        raise RuntimeError("Failed to load file as toml data") from err