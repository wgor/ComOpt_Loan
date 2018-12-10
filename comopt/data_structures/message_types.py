from typing import List, Optional, Union, Tuple
from datetime import datetime, timedelta

from numpy import ndarray
from pandas import Series

from comopt.data_structures.commitments import (
    PiecewiseConstantProfileCommitment,
    DeviationCostCurve,
)


class Request:
    """Todoc: write docstring, including explanation that the optional costs refer to the whole Offer (not per timeslot)."""

    def __init__(
        self,
        id: int,
        requested_values: Union[List[float], ndarray, Series],
        deviation_cost_curve: Optional[DeviationCostCurve] = None,
        costs: Optional[float] = None,
        start: datetime = None,
        end: datetime = None,
        resolution: timedelta = None,
    ):
        self.id = id
        self.requested_values = requested_values
        self.commitment = PiecewiseConstantProfileCommitment(
            label="Requested commitment",
            constants=requested_values,
            deviation_cost_curve=deviation_cost_curve,
            start=start,
            end=end,
            resolution=resolution,
        )
        self.start = self.commitment.start
        self.end = self.commitment.end
        self.duration = self.commitment.duration
        self.resolution = self.commitment.resolution
        self.costs = costs


class Offer:
    """Todoc: write docstring, including explanation that costs refer to the whole Offer (not per timeslot)."""

    def __init__(
        self,
        id: int,
        offered_values: Union[List[float], ndarray, Series, Tuple],
        deviation_cost_curve: Optional[DeviationCostCurve],
        costs: Optional[float],
        start: datetime = None,
        end: datetime = None,
        resolution: timedelta = None,
    ):
        self.id = id
        self.offered_values = offered_values
        self.commitment = PiecewiseConstantProfileCommitment(
            label="Offered commitment",
            constants=offered_values,
            deviation_cost_curve=deviation_cost_curve,
            start=start,
            end=end,
            resolution=resolution,
        )
        self.start = self.commitment.start
        self.end = self.commitment.end
        self.duration = self.commitment.duration
        self.resolution = self.commitment.resolution
        self.costs = costs
        self.accepted = (
            None
        )  # Boolean attribute that can be set later on to say whether the offer lead to an order


class Order:
    """Todoc: write docstring, including explanation that costs refer to the whole Offer (not per timeslot)."""

    # Todo: would be nice if you could also simply initialise an Order by passing it an Offer
    def __init__(
        self,
        id: int,
        ordered_values: Union[List[float], ndarray, Series],
        deviation_cost_curve: DeviationCostCurve,
        costs: float,
        start: datetime = None,
        end: datetime = None,
        resolution: timedelta = None,
    ):
        self.id = id
        self.commitment = PiecewiseConstantProfileCommitment(
            label="Actual commitment",
            constants=ordered_values,
            deviation_cost_curve=deviation_cost_curve,
            start=start,
            end=end,
            resolution=resolution,
        )
        self.start = self.commitment.start
        self.end = self.commitment.end
        self.duration = self.commitment.duration
        self.resolution = self.commitment.resolution
        self.costs = costs


class Prognosis(Offer):
    """A Prognosis is just an Offer with undefined costs and deviation cost curve."""

    def __init__(self, prognosed_values: Union[List[float], ndarray, Series], **kwargs):
        super(Prognosis, self).__init__(
            offered_values=prognosed_values,
            deviation_cost_curve=None,
            costs=None,
            **kwargs
        )
