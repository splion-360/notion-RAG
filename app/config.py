import logging
import os
from typing import Literal

from dotenv import load_dotenv
from pydantic_settings import BaseSettings


class AppSettings(BaseSettings):
    name: str = "Notion Search"
    description: str = "Semantic search over user's notion pages"
    version: str = "v1.0.0"
    prefix: str = "/api/v1"
    allowed_origins: list = ["*"]


settings = AppSettings()
load_dotenv()


# Fetch all the environment secrets
ENVIRONMENT = os.environ.get("ENVIRONMENT", "development")
PIPEDREAM_CLIENT_ID = os.environ.get("PIPEDREAM_CLIENT_ID")
PIPEDREAM_CLIENT_SECRET = os.environ.get("PIPEDREAM_CLIENT_SECRET")
PIPEDREAM_PROJECT_ID = os.environ.get("PIPEDREAM_PROJECT_ID")
PIPEDREAM_OAUTH_APP_ID = os.environ.get("PIPEDREAM_OAUTH_APP_ID")

if ENVIRONMENT == "development":
    SUPABASE_URL = os.environ.get("SUPABASE_URL_DEV")
    SUPABASE_KEY = os.environ.get("SUPABASE_SECRET_KEY_DEV")
else:
    SUPABASE_URL = os.environ.get("SUPABASE_URL")
    SUPABASE_KEY = os.environ.get("SUPABASE_SECRET_KEY")


LOG_COLORS = {
    "RED": "\033[31m",
    "GREEN": "\033[32m",
    "YELLOW": "\033[33m",
    "BLUE": "\033[34m",
    "MAGENTA": "\033[35m",
    "CYAN": "\033[36m",
    "WHITE": "\033[37m",
    "BRIGHT_RED": "\033[91m",
    "BRIGHT_GREEN": "\033[92m",
    "BRIGHT_YELLOW": "\033[93m",
    "RESET": "\033[0m",
}

ColorType = Literal[
    "RED",
    "GREEN",
    "YELLOW",
    "BLUE",
    "MAGENTA",
    "CYAN",
    "WHITE",
    "BRIGHT_RED",
    "BRIGHT_GREEN",
    "BRIGHT_YELLOW",
]


class ColoredFormatter(logging.Formatter):
    def __init__(self, fmt: str):
        super().__init__(fmt)
        self.colors = {
            logging.DEBUG: "BRIGHT_YELLOW",
            logging.INFO: "GREEN",
            logging.WARNING: "YELLOW",
            logging.ERROR: "RED",
            logging.CRITICAL: "BRIGHT_RED",
        }

    def format(self, record):
        message = super().format(record)
        if hasattr(record, "custom_color") and record.custom_color:
            color = record.custom_color
        else:
            color = self.colors.get(record.levelno, "WHITE")
        return f"{LOG_COLORS[color]}{message}{LOG_COLORS['RESET']}"


class CustomLogger:
    def __init__(self, logger: logging.Logger):
        self._logger = logger

    def info(self, message: str, color: ColorType = None):
        record = self._logger.makeRecord(self._logger.name, logging.INFO, "", 0, message, (), None)
        if color:
            record.custom_color = color
        self._logger.handle(record)

    def debug(self, message: str, color: ColorType = None):
        record = self._logger.makeRecord(self._logger.name, logging.DEBUG, "", 0, message, (), None)
        if color:
            record.custom_color = color
        self._logger.handle(record)

    def warning(self, message: str, color: ColorType = None):
        record = self._logger.makeRecord(
            self._logger.name, logging.WARNING, "", 0, message, (), None
        )
        if color:
            record.custom_color = color
        self._logger.handle(record)

    def error(self, message: str, color: ColorType = None):
        record = self._logger.makeRecord(self._logger.name, logging.ERROR, "", 0, message, (), None)
        if color:
            record.custom_color = color
        self._logger.handle(record)

    def __getattr__(self, name):
        return getattr(self._logger, name)


def setup_logger(name: str = __name__) -> CustomLogger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return CustomLogger(logger)

    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    handler.setLevel(logging.INFO)
    formatter = ColoredFormatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.propagate = False

    return CustomLogger(logger)


logger = setup_logger(__name__)
