import logging
from typing import List, Optional

FORMAT_STR_VERBOSE_INFO = '{ %(name)s:%(lineno)d @ %(asctime)s } -'

CLI_LOGGERS: List[logging.Logger] = []
CODE_LOGGERS: List[logging.Logger] = []
CLI_LOG_LEVEL = logging.INFO
CODE_LOG_LEVEL = logging.WARNING

tool_name = 'mcal'

def get_logger(name: str, cli: bool = False) -> logging.Logger:
    """
    Returns a logger with some helpful presets.

    Args:
        name (str): The module name of course.

    Returns:
        logging.Logger: A python logger.
    """
    logger = logging.getLogger(name)

    handler = logging.StreamHandler()
    if cli:
        formatter = CLIFormatter()
    else:
        formatter = logging.Formatter(
            f'[{tool_name}] %(levelname)s - {FORMAT_STR_VERBOSE_INFO} %(message)s'
        )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    logger.propagate = True

    if cli:
        logger.setLevel(CLI_LOG_LEVEL)
        CLI_LOGGERS.append(logger)
    else:
        logger.setLevel(CODE_LOG_LEVEL)
        CODE_LOGGERS.append(logger)

    return logger

def set_cli_level(
    level: int,
    extra_modules: Optional[List[str]] = None
):
    """
    Set all CLI loggers to a specific logging level.

    Args:
        level (int): The logging level to set
    """
    cli_level = logging.INFO
    code_level = logging.WARNING

    if level == 1:
        cli_level = logging.DEBUG
    elif level == 2:
        cli_level = logging.DEBUG
        code_level = logging.INFO
    elif level >= 3:
        cli_level = logging.DEBUG
        code_level = logging.DEBUG

    for logger in CODE_LOGGERS:
        logger.setLevel(code_level)
    for logger in CLI_LOGGERS:
        logger.setLevel(cli_level)
    if extra_modules is not None:
        for module in extra_modules:
            get_logger(module).setLevel(cli_level)

    # Store for any loggers created after this invocation
    global CLI_LOG_LEVEL
    global CODE_LOG_LEVEL
    CLI_LOG_LEVEL = cli_level
    CODE_LOG_LEVEL = code_level

class CLIFormatter(logging.Formatter):
    """
    Logging formatter to change format based on level
    """
    info_format = f'[{tool_name}] %(message)s'
    default_format = f'[{tool_name}] %(levelname)s - %(message)s'

    def __init__(self):
        super().__init__(self.default_format)

    def format(self, record: logging.LogRecord) -> str:
        if record.levelno == logging.INFO:
            self._style._fmt = self.info_format
        else:
            self._style._fmt = self.default_format

        return super().format(record)