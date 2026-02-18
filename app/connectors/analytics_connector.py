
import json
from pathlib import Path
from .base import BaseConnector

class AnalyticsConnector(BaseConnector):

    def fetch(self, **kwargs):
        with open(Path("data/analytics.json")) as f:
            return json.load(f)
