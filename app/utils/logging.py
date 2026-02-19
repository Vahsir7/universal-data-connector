"""Logging configuration helper.

Uses importlib to import the standard-library logging module so the
module name 'logging.py' does not shadow it.
"""

import importlib

# Import stdlib logging via importlib to avoid circular shadowing
# (this file is named logging.py which would otherwise shadow stdlib logging)
std_logging = importlib.import_module("logging")

def configure_logging():
    std_logging.basicConfig(
        level=std_logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    )
