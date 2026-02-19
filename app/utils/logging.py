
import importlib

std_logging = importlib.import_module("logging")

def configure_logging():
    std_logging.basicConfig(
        level=std_logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    )
