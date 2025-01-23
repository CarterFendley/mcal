import os

from jinja2 import BaseLoader, Environment, StrictUndefined

from k_calibrate.utils.logging import get_logger

THIS_DIR = os.path.abspath(os.path.dirname(__file__))

logger = get_logger(__name__)

def load_sql(file: str, arguments: dict) -> str:
    path = os.path.join(THIS_DIR, file)
    assert os.path.isfile(path), "Pat does not exist: %s" % path

    env = Environment(
        loader=BaseLoader(),
        undefined=StrictUndefined
    )
    with open(path, 'r') as f:
        template = env.from_string(f.read())

    rendered = template.render(arguments)
    logger.debug("Rendered SQL query:\n%s" % rendered)
    return rendered