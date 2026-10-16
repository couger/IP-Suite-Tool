"""Bounded diagnostic events. User data and exception messages are not logged."""
import logging
from logging.handlers import RotatingFileHandler

from utils.app_paths import data_directory


class PrivateDataSafeFormatter(logging.Formatter):
    """F-strings can already contain data, so do not format the message at all."""
    def format(self, record):
        timestamp = self.formatTime(record, "%Y-%m-%d %H:%M:%S")
        event = f"{record.name}:{record.funcName}:{record.lineno}"
        error = ""
        if record.exc_info and record.exc_info[0]:
            error = f" exception={record.exc_info[0].__name__}"
        return f"{timestamp} {record.levelname} {event}{error}"


def setup_module_logger(module_name, log_level=logging.INFO):
    logger = logging.getLogger(module_name)
    logger.setLevel(log_level)
    logger.propagate = False
    if not logger.handlers:
        directory = data_directory() / "logs"
        directory.mkdir(exist_ok=True)
        handler = RotatingFileHandler(directory / f"{module_name}.log", maxBytes=262144, backupCount=2, encoding="utf-8")
        handler.setFormatter(PrivateDataSafeFormatter())
        logger.addHandler(handler)
    return logger


def setup_logging(log_name="app", log_level=logging.INFO):
    return setup_module_logger(log_name, log_level)


def get_application_path():
    return str(data_directory())
