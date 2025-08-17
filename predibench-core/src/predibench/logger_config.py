import logging
import os

import coloredlogs

FORMAT = "%(asctime)s %(hostname)s %(name)s:%(lineno)d %(levelname)s %(message)s"
FIELD_STYLES = coloredlogs.DEFAULT_FIELD_STYLES | {"levelname": {"color": "magenta"}}
DEFAULT_LOG_LEVEL = logging.INFO


def get_logger(name: str, level: int | None = None):
    """
    Configures and returns a logger with colored output.

    The log level can be set via the COLOREDLOGS_LOG_LEVEL environment variable
    or by explicitly passing the 'level' argument. Defaults to INFO.
    """
    log_level = level if level is not None else os.environ.get("COLOREDLOGS_LOG_LEVEL")
    coloredlogs.install(
        level=log_level or DEFAULT_LOG_LEVEL,
        fmt=FORMAT,
        field_styles=FIELD_STYLES,
        logger=logging.getLogger(name),
        isatty=True,
    )
    return logging.getLogger(name)
