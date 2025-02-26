from __future__ import annotations

import fcntl
import json
import os
import shutil
from typing import Generic, Type, TypeVar

from pydantic import BaseModel

from mcal.utils.logging import get_logger

T = TypeVar('T', bound=BaseModel)

logger = get_logger(__name__)

# TODO:
# 1. A few synchronization things to check
# 2. Deleting logic is maybe a little messy
#   -> Plus fixture out how other processes should react to deleted file.
class SharedModel(Generic[T]):
    @staticmethod
    def validate_path(path: str):
        assert path.endswith(".json")

    @classmethod
    def initialize(cls, model: T, path: str) -> SharedModel[T]:
        cls.validate_path(path)
        assert not os.path.exists(path), "Specified file path already exists"

        with open(path, 'w') as f:
            json.dump(model.model_dump_json(), f)

        return cls(model.__class__, path)

    def __init__(self, model_cls: Type[T], path: str):
        self.validate_path(path)

        self.model_cls = model_cls
        self.path = path

        self._shared_file = None
        self._model = None

        self._deleting = False
        self.deleted = False

    def __enter__(self) -> T:
        # TODO: Detect multiple of these in the same thread?
        assert self._shared_file is None, "Duplicate call to the SharedModel context manager, exit context before re-enter."

        self._shared_file = open(self.path, 'r+')
        fcntl.flock(self._shared_file.fileno(), fcntl.LOCK_EX)

        self._model = self.model_cls.model_validate_json(
            json.load(self._shared_file)
        )

        return self._model

    @property
    def deleting_path(self) -> str:
        return self.path + ".deleting"

    def mark_for_delete(self):
        assert self._shared_file is not None, "Mark for delete should only be done while the context is entered."
        assert not self._deleting and not self.deleted, "Cannot mark already marked or already deleted file for deletion."

        self._deleting = True
        shutil.move(self.path, self.deleting_path)

    def delete(self):
        assert self._shared_file is not None, "Delete should only be one while the context is entered."
        assert not self.deleted, "Cannot delete already deleted file."


        self._shared_file.close()
        if self._deleting:
            os.remove(self.deleting_path)
        else:
            os.remove(self.path)

        print("Deleted!!")
        self.deleted = True

    def __exit__(self, exc_type, exc_value, exc_tb):
        if self.deleted:
            self._shared_file = None
            self._model = None
            return

        if self._deleting and not self.deleted:
            # `not self.deleted` is redundant given above clause but :shrug:
            logger.warning("Context exited after previously marking shared model file for deletion but no subsequent deletion. Restoring file...")
            shutil.move(self.deleting_path, self.path)
            self._deleting = False

        assert self._shared_file is not None, "Context exited before enter, enter context first."

        self._shared_file.seek(0)
        json.dump(self._model.model_dump_json(), self._shared_file)

        fcntl.flock(self._shared_file.fileno(), fcntl.LOCK_UN)
        self._shared_file.close()

        self._shared_file = None
        self._model = None