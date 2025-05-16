import json
import os
from pathlib import Path
from random import shuffle
from typing import List

import dspy
from loguru import logger

from ..config import DEFAULT_APPROVER_MODEL, SimpleConfig

# UNDER DEVELOPMENT, THIS DOESN'T WORK YET
openapi_key = os.environ["OPENAI_API_KEY"]
lm = dspy.LM(DEFAULT_APPROVER_MODEL, api_key=openapi_key)


def load_change_data(file_path: Path):
    dspy_examples: List[dspy.Example] = []
    inputs = ["issue_type", "issue_message", "content_before", "content_after"]
    with open(file_path, "r") as f:
        for line in f.readlines():
            as_json = json.loads(line)

            dspy_examples.append(dspy.Example(**as_json).with_inputs(*inputs))

    return dspy_examples


def split_train_test(data, train_percentage=0.5):
    """Split data into train and test sets based on a percentage.

    Args:
        data: List of examples to split
        train_percentage: Percentage of data to use for training (default: 0.8)

    Returns:
        tuple: (train_data, test_data)
    """
    if not data:
        return [], []

    shuffle_data = data.copy()
    shuffle(shuffle_data)

    split_idx = int(len(shuffle_data) * train_percentage)
    train_data = shuffle_data[:split_idx]
    test_data = shuffle_data[split_idx:]

    return train_data, test_data


def approval_metric(gold, predicted, trace=None):
    if gold.approved == predicted.approved:
        return 1
    return 0


class Approver(dspy.Signature):
    """Determine whether or not a particular change should be approved."""

    issue_type: str = dspy.InputField()
    issue_message: List[str] = dspy.InputField()
    content_before: str = dspy.InputField()
    content_after: str = dspy.InputField()
    approved: bool = dspy.OutputField()


def load_module():
    return dspy.ChainOfThought(Approver)


def train_module_small(data: List[dspy.Example]):
    optimizer = dspy.BootstrapFewShot(metric=approval_metric)
    module = load_module()
    return optimizer.compile(module, trainset=data)


def train_module(config: SimpleConfig):
    labelled_data = load_change_data(config.get_approval_path())
    logger.info(f"Found {len(labelled_data)} examples")
    if len(labelled_data) < 15:
        logger.error("Not enough examples to train a model")
    with dspy.context(lm=lm):
        if len(labelled_data) < 30:
            train, test = split_train_test(labelled_data)
            compiled = train_module_small(train)
            evaluate = dspy.Evaluate(devset=train, metric=approval_metric)
            evaluate(compiled)
