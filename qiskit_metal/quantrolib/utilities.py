"""Utility functions for the quantrolib package."""

# built-in packages
from pathlib import Path

# external packages
import yaml

from qiskit_metal.quantrolib.logger import logger


def load_yaml(file_path: Path) -> dict:
    """Loads a YAML file and return its contents as a dictionary.

    Parameters
    ----------
    file_path : Path
        Path to the YAML file.

    Returns
    -------
    dict
        Contents of the YAML file.
    """
    with open(file_path, "r") as file:
        return yaml.safe_load(file)
