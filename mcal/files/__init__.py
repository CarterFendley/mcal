import os
from tempfile import NamedTemporaryFile
from typing import Optional

from jinja2 import BaseLoader, Environment, StrictUndefined

from mcal.utils.logging import get_logger

THIS_DIR = os.path.abspath(
    os.path.dirname(__file__)
)

K8_NR_HELM_VALUES = 'k8/newrelic-helm-values.yaml'

logger = get_logger(__name__)

def load_file(
    file: str,
    arguments: Optional[dict] = None,
    log_rendered: bool = False
):
    path = os.path.join(THIS_DIR, file)
    assert os.path.isfile(path), "Path does not exist: %s" % path

    if arguments is None:
        arguments = {}

    env = Environment(
        loader=BaseLoader(),
        undefined=StrictUndefined
    )
    with open(path, 'r') as f:
        template = env.from_string(f.read())

    rendered = template.render(arguments)
    if log_rendered:
        logger.debug("Rendered file '%s':\n%s" % (path, rendered))
    return rendered

def load_to_temp_file(
    file: str,
    arguments: Optional[dict] = None,
    log_rendered: bool = False
) -> NamedTemporaryFile:
    rendered = load_file(
        file=file,
        arguments=arguments,
        log_rendered=log_rendered
    )

    tmp_file = NamedTemporaryFile(suffix='.yaml')
    with open(tmp_file.name, 'w') as f:
        f.write(rendered)
        f.seek(0) # NOTE: Honestly can't remember if I need to this

    return tmp_file