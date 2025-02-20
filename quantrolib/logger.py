import logging


def setup_package_logger():
    """Sets up a logger for the package."""
    logger = logging.getLogger("quantrolib")
    logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    handler.setLevel(logging.INFO)

    logger.addHandler(handler)

    return logger

logger = setup_package_logger()
