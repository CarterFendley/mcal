import logging

from k_calibrate.utils.logging import get_logger, set_cli_level


def test_basic(caplog):
    logger = get_logger(__name__)
    with caplog.at_level(logging.DEBUG):
        logger.error("Error")
        logger.warning("Warning")
        logger.info("Info")
        logger.debug("Debug")

    # NOTE: Honestly not sure how useful these assertions are
    assert caplog.record_tuples == [
        (__name__, logging.ERROR, "Error"),
        (__name__, logging.WARNING, "Warning"),
        (__name__, logging.INFO, "Info"),
        (__name__, logging.DEBUG, "Debug"),
    ]

def test_cli_logging(caplog):
    cli_logger = get_logger('cli', cli = True)
    code_logger = get_logger('code', cli = False)

    cli_logger.info("CLI Info")
    code_logger.info("Code Info")
    assert caplog.record_tuples == [
        ('cli', logging.INFO, "CLI Info")
    ]

    set_cli_level(1)
    caplog.clear()
    cli_logger.debug("CLI Debug")
    code_logger.info("Code Info")
    assert caplog.record_tuples == [
        ('cli', logging.DEBUG, "CLI Debug")
    ]

    set_cli_level(2)
    caplog.clear()
    cli_logger.debug("CLI Debug")
    code_logger.info("Code Info")
    assert caplog.record_tuples == [
        ('cli', logging.DEBUG, "CLI Debug"),
        ('code', logging.INFO, "Code Info")
    ]

    set_cli_level(3)
    caplog.clear()
    cli_logger.debug("CLI Debug")
    code_logger.debug("Code Debug")
    assert caplog.record_tuples == [
        ('cli', logging.DEBUG, "CLI Debug"),
        ('code', logging.DEBUG, "Code Debug")
    ]