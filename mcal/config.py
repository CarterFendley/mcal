from __future__ import annotations

import importlib
import inspect
import os
from typing import Any, Callable, Dict, List, Optional, Tuple

import jinja2
import oyaml as yaml
from jinja2 import BaseLoader, Environment
from pydantic import BaseModel, ConfigDict, Field, model_validator

from mcal.actions import Action
from mcal.calibrate import (
    Sampler,
    Schedule,
    get_sampler,
    get_schedule,
    is_sampler,
    is_schedule,
)
from mcal.utils.logging import get_logger
from mcal.watchers import Watcher

logger = get_logger(__name__)

class KindArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: str
    args: Optional[Dict[str, Any]] = Field(default_factory=lambda: {})

class SamplerConfig(KindArgs):
    name: Optional[str] = None

    @model_validator(mode='after')
    def check_sampler_config(self) -> SamplerConfig:
        if not is_sampler(self.kind):
            raise ValueError("Specified sampler does not exist: %s" % self.kind)

        return self

    def get_name(self) -> str:
        if self.name is not None:
            return self.name
        return self.kind

class ScheduleConfig(KindArgs):
    @model_validator(mode='after')
    def check_sampler_config(self) -> ScheduleConfig:
        if not is_schedule(self.kind):
            raise ValueError("Specified schedule does not exist: %s" % self.kind)

        return self

class ObjectAsKind(KindArgs):
    _object: Callable = None

    def create_object(
        self,
        builtin_module: str,
        always_construct: bool = False
    ):
        try:
            module_path, obj_name= self.kind.split(":")

            if module_path == 'builtin':
                module_path = builtin_module

            assert module_path != ''
            assert obj_name != ''
        except Exception as err:
            raise ValueError("Failed to treat 'kind' as 'module.path:obj' string") from err

        try:
            module = importlib.import_module(module_path)
        except Exception as err:
            # TODO: Pydantic doesn't report the `from err` part, so errors like import issues are obscured
            raise ValueError("Failed to load module specified by 'kind': %s" % (module_path)) from err

        if not hasattr(module, obj_name):
            raise ValueError("Module '%s' has no attribute '%s'" % (module_path, obj_name))
        obj = getattr(module, obj_name)

        if len(self.args) != 0 or always_construct:
            # TODO: More validation
            # 1. Look at signature? (for params / stats validation)
            # 2. Make abstract class?
            try:
                obj = obj(**self.args)
            except Exception as err:
                logger.error("Failed to construct object, args were supplied indicating that '%s' should be curried / constructed. Are the correct arguments passed: %s" % (obj_name, self.args))
                logger.error("Exception raised: %s" % err)

                raise ValueError("Failed to construct criteria function given supplied args.") from err

        self._object = obj

class WatcherConfig(ObjectAsKind):
    @model_validator(mode='after')
    def check_object_as_kind(self) -> WatcherConfig:
        # Validate watcher
        self.create_object('mcal.watchers.builtin', always_construct=True)

        if not isinstance(self._object, Watcher):
            raise ValueError("Object specified by '%s' is not a watcher: %s - %s" % (self.kind, type(self._object), self._object))

        return self

class ActionConfig(ObjectAsKind):
    @model_validator(mode='after')
    def check_function_as_kind(self) -> ActionConfig:
        # Validate action
        self.create_object('mcal.actions.builtin', always_construct=True)

        if not isinstance(self._object, Action):
            raise ValueError("Object specified by '%s' is not a action: %s - %s" % (self.kind, type(self._object), self._object))
        return self

class StopCriteriaConfig(ObjectAsKind):
    @model_validator(mode='after')
    def check_function_as_kind(self) -> StopCriteriaConfig:
        # Validate stop_criteria
        self.create_object('mcal.criteria')
        return self

class MCalConfig(BaseModel): 
    model_config = ConfigDict(extra="forbid")

    schedule: ScheduleConfig
    samplers: List[SamplerConfig]
    watchers: List[WatcherConfig] = Field(default_factory=lambda: [])
    stop_criteria: StopCriteriaConfig = Field(default=None)
    actions: List[ActionConfig] = Field(default_factory=lambda: [])

    _schedule: Schedule = None
    _samplers: Dict[str, Sampler] = None


    @model_validator(mode='after')
    def check_model(self) -> MCalConfig:
        # Validate sampler names are unique
        names = set()
        for sampler in self.samplers:
            if sampler.get_name() in names:
                raise ValueError(f"Found duplicate sampler name: {sampler.get_name()}")
            names.add(sampler.get_name())

        return self

    def save(self, path: str, override: bool = False):
        if not override:
            assert not os.path.exists(path), "Specified path already exists: %s" % path

        # Make parents if needed
        os.makedirs(os.path.dirname(path), exist_ok=True)
        data = self.model_dump()
        with open(path, 'w') as f:
            yaml.dump(data, f)

    def get_stop_criteria(self) -> Optional[Callable]:
        if self.stop_criteria is not None:
            return self.stop_criteria._object

    def create(self) -> Tuple[Schedule, Dict[str, Sampler], List[Watcher], List[Action], Callable]:
        if self._schedule is not None or self._samplers is not None:
            assert self._schedule is not None and self._samplers is not None, "Schedule or sampler has been constructed but not both. This should not happen."

            return (
                self._schedule,
                self._samplers,
                list(map(lambda x: x._object, self.watchers)),
                list(map(lambda x: x._object, self.actions)),
                self.get_stop_criteria()
            )

        # NOTE: Here we are constructing samplers first, bc schedule constructors may be permitted to use samplers to measure parameters for use in schedule. Note how samplers are passed into schedule construction.
        samplers = {}
        for sampler_config in self.samplers:
            sampler_cls = get_sampler(sampler_config.kind)
            # Sanity check although this should never be None
            assert sampler_cls is not None, "Internal error, sampler '%s' does not exist, is config validation working properly?" % sampler_config.kind

            try:
                sampler = sampler_cls(
                    **sampler_config.args
                )
                samplers[sampler_config.get_name()] = sampler
            except Exception as err:
                logger.error("Failed to construct sampler '%s' with arguments: %s" % (sampler_config.kind, sampler_config.args))
                logger.error("Please make sure the arguments are correct and initialization logic.")
                logger.error(err)
                raise err

        schedule_cls = get_schedule(self.schedule.kind)
        # Another sanity check that should never be false
        assert schedule_cls is not None, "Internal error, schedule '%s' does not exist, is config validation working properly?" % self.schedule.kind

        try:
            signature = inspect.signature(schedule_cls.from_config)

            if 'samplers' in signature.parameters:
                assert 'samplers' not in self.schedule.args, "Usage error, parameter name 'samplers' is reserved for injection of samplers"
                schedule = schedule_cls.from_config(
                    **self.schedule.args,
                    samplers=samplers
                )
            else:
                schedule = schedule_cls.from_config(
                    **self.schedule.args,
                )
        except Exception as err:
            logger.error("Failed to construct schedule '%s' with arguments: %s" % (self.schedule.kind, self.schedule.args))
            logger.error("Please make sure the arguments are correct and initialization logic.")
            logger.error(err)
            raise err

        # If everything works, save constructions and return
        self._schedule = schedule
        self._samplers = samplers

        return (
            schedule,
            samplers,
            list(map(lambda x: x._object, self.watchers)),
            list(map(lambda x: x._object, self.actions)),
            self.get_stop_criteria()
        )

def load_config_file(path: str, arguments: Dict[str, Any]) -> MCalConfig:
    assert os.path.isfile(path), "Config path is not a file: %s" % path
    with open(path, 'r') as f:
        return load_config(f.read(), arguments, file_path=path)

def load_config(string: str, arguments: Dict[str, Any], file_path: str = None) -> MCalConfig:
    # Render variables if they exist
    if file_path is not None:
        loader = jinja2.FileSystemLoader(os.path.dirname(file_path))
    else:
        loader = BaseLoader()
    env = Environment(
        loader=loader,
        undefined=jinja2.StrictUndefined
    )
    template = env.from_string(string)
    rendered = template.render(arguments)

    # Load into pydantic model
    data = yaml.safe_load(rendered)
    assert isinstance(data, dict), "Could not load any data from rendered string"
    model = MCalConfig.model_validate(data)

    return model