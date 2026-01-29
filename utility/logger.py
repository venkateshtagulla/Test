"""
Logging helpers.
"""
import logging


def get_logger(name: str) -> logging.Logger:
    """
    Provide a configured logger instance.
    """

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    return logging.getLogger(name)

