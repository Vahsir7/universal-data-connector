
import json
from pathlib import Path
from .base import BaseConnector

class CRMConnector(BaseConnector):

    def fetch(self, **kwargs):
        with open(Path("data/customers.json")) as f:
            return json.load(f)
