import json
from typing import List

import dspy


def load_change_data(file_path: str):
    dspy_examples: List[dspy.Example] = []
    with open(file_path, "r") as f:
        for line in f.readlines():
            as_json = json.loads(line)
            dspy_examples.append(dspy.Example(**as_json))
