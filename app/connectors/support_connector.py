
import json
from pathlib import Path
from .base import BaseConnector

class SupportConnector(BaseConnector):

    def fetch(self, **kwargs):
        with open(Path("data/support_tickets.json")) as f:
            return json.load(f)
