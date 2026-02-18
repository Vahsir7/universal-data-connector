
from typing import List, Dict

def summarize_if_large(data: List[Dict]) -> List[Dict]:
    if len(data) > 10:
        return [{"summary": f"{len(data)} records found. Showing first 10."}]
    return data
