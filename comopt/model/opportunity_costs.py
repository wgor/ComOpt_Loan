from typing import List
from datetime import datetime, timedelta

from pandas import Series

from comopt.data_structures.commitments import (
    PiecewiseConstantProfileCommitment as Commitment
)
from comopt.model.utils import initialize_series


def determine_opportunity_costs_model_a(
    previous_commitments: List[List[Commitment]],
    start: datetime,
    end: datetime,
    resolution: timedelta,
) -> Series:
    """Always expect to make 1 buck. Just a silly implementation to get us started.
    Previous commitments is a list of commitments per EMS, i.e. a list of lists."""
    return initialize_series(1, start, end, resolution)


def determine_opportunity_costs_model_b(
    previous_commitments: List[List[Commitment]],
    start: datetime,
    end: datetime,
    resolution: timedelta,
) -> Series:
    # Todo: set up at least one more model to determine opportunity costs
    # Todo (not urgent): slowly decay opportunity costs (to model a discounted sum of future returns)
    return initialize_series(0, start, end, resolution)
