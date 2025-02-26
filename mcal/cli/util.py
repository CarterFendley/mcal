import re
import sys

from mcal.utils.logging import get_logger

logger = get_logger(__name__, cli=True)

def parse_extra_kwargs(context) -> dict:
    kwargs = {}
    for kv_pair in context.args:
        if not re.match(r"--[^=]+=[^=]+", kv_pair):
            logger.error("Extra arg provided which does not follow '--key=value' pattern: '%s'" % kv_pair)
            sys.exit(1)

        # TODO: Type comparison / conversion to needed type?
        key, value = kv_pair[2:].split('=')
        kwargs[key] = value

    return kwargs