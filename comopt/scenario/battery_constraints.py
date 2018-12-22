from datetime import datetime, timedelta
from typing import Tuple

from pandas import DataFrame

from comopt.scenario.ems_constraints import completely_unconstrained_profile


def limited_battery_capacity_profile(
    start: datetime,
    end: datetime,
    resolution: timedelta,
    battery_power_capacity: float,
    soc_limits: Tuple[float, float],
    soc_start: float,
) -> DataFrame:
    df = completely_unconstrained_profile(start=start, end=end, resolution=resolution)
    df["derivative max"] = battery_power_capacity
    df["derivative min"] = -battery_power_capacity
    df["soc min"] = soc_limits[0]
    df["soc max"] = soc_limits[1]
    # df["soc"]
    # df["equals"].iloc[0] = soc_start
    return df
