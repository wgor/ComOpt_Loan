from typing import List, Optional, Tuple, Union
from datetime import datetime, timedelta

from pandas import Series, to_timedelta
import numpy as np
from numpy import ndarray
import matplotlib.pyplot as plt

from comopt.model.utils import initialize_series


class DeviationCostCurve:
    """
    A deviation cost curve represents the penalty (e.g. in EUR) for deviating from the committed flow (e.g. in MW) in a
    certain timeslot.
        gradient:
            Determines the gradient of the linear cost curve (e.g. in EUR/MWh) for a linear cost function.
            Can be a tuple to specify two different slopes for downwards and upwards deviations.

        flow_unit_multiplier
            The flow unit multiplier specifies how to convert from a unit of flow into a unit of change in stock, given
            the resolution of the flow (the profile commitment).
            I.e. 1 unit of flow (over the resolution of the profile commitment) results in 1 * flow_unit_multiplier
            units of change in stock.
    """

    def __init__(
        self,
        flow_unit_multiplier: float,
        gradient: Union[float, Tuple[float]] = None,
    ):

        if isinstance(gradient, tuple):
            self.gradient_down = (
                gradient[0] * flow_unit_multiplier
            )  # E.g. in EUR/(MW*15min) rather than EUR/MWh
            self.gradient_up = gradient[1] * flow_unit_multiplier
            # Todoc: delete these comments
            # our commitment 10 MW, we end up using 11 MW, costs will be (11-10)MW * 1 EUR/(MW*15min) * 15min (from timeseries resolution)
            # our commitment 10 MW, we end up using 11 MW, costs will be (11-10)MW * 1 EUR/MWh * h(how do I know it's an hour)
        else:
            self.gradient_down = gradient * flow_unit_multiplier
            self.gradient_up = gradient * flow_unit_multiplier
        return
    
    def cost_decorator(func):
        def wrapper(self, quantity):

            assert self.gradient is not None, "No GRADIENT VALUE - Please pass one!"
            self.func = (
                lambda quantity: quantity * self.gradient_up
                if quantity >= 0
                else -quantity * self.gradient_down
            )

            return func(self, quantity)

        return wrapper

    @cost_decorator
    def get_costs(self, quantity):
        return self.func(quantity)

    def plot(self, quantity=None):
        x1 = np.linspace(-30, 30, 1000)
        y1 = [self.get_costs(x) for x in x1]
        plt.plot(x1, y1, drawstyle="steps", label="committed profile")
        return plt.show()


class PiecewiseConstantProfileCommitment:
    """
    # Todoc: annotate the superclasses or the PCPC class explaining the meaning of nan values (namely nan = no commitment)
    label:
            Can be used to label the commitment (useful for debugging).
    constants:
            The EM-System(s) feed in energy to the grid (=negative net_demand)
            or energy drawn from the grid (=positive net_demand), for each timeperiod .
    deviation_cost_curve:
            Indicates deviation cost curve that gets assigned for each timeperiod.
    """

    def __init__(
        self,
        label: Optional[str],
        constants: Union[List[float], ndarray, Series],
        deviation_cost_curve: Optional[DeviationCostCurve],
        revenue: float = None,
        start: datetime = None,
        end: datetime = None,
        resolution: timedelta = None,
        costs: float = None,
    ):
        self.label = label
        self.deviation_cost_curve = deviation_cost_curve
        self.costs = costs
        if isinstance(constants, (list, ndarray)) or constants is None:
            if start is None or end is None or resolution is None:
                raise Exception("Missing time information at initialization.")
            self.constants = initialize_series(constants, start, end, resolution)
            self.start = start
            self.end = end
            self.duration = end - start
            self.resolution = resolution
        else:
            self.constants = constants
            self.start = constants.index.values[0]
            self.resolution = to_timedelta(constants.index.freq)
            self.end = constants.index.values[-1] + self.resolution
            self.duration = self.end - self.start

    def cost_vector(self, quantities: List[float]):
        return [self.deviation_cost_curve.get_costs(q) for q in quantities]

    def get_total_costs(self, quantities: List[float]):
        return sum(self.cost_vector(quantities))
