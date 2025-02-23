import logging

import pytest

from k_calibrate import compare
from k_calibrate.compare import respond_to_event
from k_calibrate.utils.logging import get_logger

logger_name = compare.__name__

def test_basic(caplog):
    get_logger(logger_name).setLevel(logging.INFO)

    # Basic warning default
    caplog.clear()
    respond_to_event(
        name='my_warning_event',
        config={},
        msg="My warning message!"
    )
    assert (logger_name, logging.WARNING, "My warning message!") in caplog.record_tuples

    # With error message
    caplog.clear()
    with pytest.raises(RuntimeError, match="Error: 'my_error_event'"):
        respond_to_event(
            name='my_error_event',
            config={
                'my_error_event': 'error'
            },
            msg="My error message!"
        )
    assert (logger_name, logging.ERROR, "My error message!") in caplog.record_tuples

    # Basic warning default
    caplog.clear()
    respond_to_event(
        name='my_default_event',
        config={
            'my_default_event': 'not_an_action'
        },
        msg="My default message!"
    )

    assert (logger_name, logging.INFO, "Invalid action 'not_an_action' for event 'my_default_event', defaulting to 'warn'.") in caplog.record_tuples
    assert (logger_name, logging.WARNING, "My default message!") in caplog.record_tuples