import logging


def setup_package_logger():
    """Sets up a logger for the package."""
    logger = logging.getLogger("quantrolib")
    logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        '%(levelname)s %(asctime)s [%(name)s]: %(message)s',
        datefmt='%I:%M%p',
    )

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    handler.setLevel(logging.INFO)

    logger.addHandler(handler)

    logger.propagate = False

    return logger


logger = setup_package_logger()
