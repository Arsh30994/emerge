"""Shared logging and error-handling helpers."""

import logging
import traceback
from functools import wraps


ERROR_LOG_FILE = "errors.log"


def setup_logging(name="singing_bowl_export", log_file=ERROR_LOG_FILE):
    """
    Configure and return a logger that writes to errors.log and the console.

    Safe to call multiple times — handlers are only attached once per logger.
    """
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    return logger


logger = setup_logging()


def log_exception(context, exc, logger_instance=None):
    """Log an exception with traceback under a short context label."""
    log = logger_instance or logger
    log.error("%s: %s", context, exc)
    log.debug(traceback.format_exc())


def safe_api_call(context="API call"):
    """
    Decorator that catches exceptions, logs them, and returns a failure dict.

    Useful for Flask route handlers that should always return JSON.
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as exc:
                log_exception(context, exc)
                return {
                    "status": "error",
                    "message": f"{context} failed: {exc}",
                }, 500

        return wrapper

    return decorator


def user_friendly_error(exc):
    """Map common exception types to short, demo-friendly messages."""
    message = str(exc).strip() or exc.__class__.__name__
    lower = message.lower()

    if "api key" in lower or "authentication" in lower or "unauthorized" in lower:
        return "Authentication failed. Check your API keys or Gmail App Password in .env."
    if "rate limit" in lower or "429" in lower or "too many" in lower:
        return "API rate limit reached. Wait a bit and try again, or reduce request volume."
    if "connection" in lower or "timeout" in lower or "network" in lower:
        return "Network error. Check your internet connection and try again."
    if "file not found" in lower or "no such file" in lower:
        return "Required data file is missing. Run the previous step first."
    return message
