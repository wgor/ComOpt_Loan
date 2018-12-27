from datetime import datetime, time, timedelta
from typing import Tuple

from pandas import DataFrame, date_range

from comopt.scenario.ems_constraints import limited_consumption_profile
from comopt.scenario.utils import time_duration, time_plus


def daily_buffer_profile(
    start: datetime,
    end: datetime,
    resolution: timedelta,
    buffer_power_capacity: float,
    buffer_storage_capacity: float,
    fill_between: Tuple[time, time],
    start_fill: float = 0,
) -> DataFrame:
    """Daily consumption for a buffer that needs to be fully filled within specific hours (fill_between).
    NB: Time values must be multiple of resolution. Function fails when given the flexibility to fill around midnight.
    """

    min_fill_duration = timedelta(hours=buffer_storage_capacity / buffer_power_capacity)
    if time_duration(*fill_between) < min_fill_duration:
        raise ValueError("Not enough time to completely fill buffer.")

    df = limited_consumption_profile(start=start, end=end, resolution=resolution, capacity=buffer_power_capacity)
    min_fill_steps = min_fill_duration // resolution
    min_empty_time = fill_between[0]
    min_full_time = time_plus(fill_between[0], min_fill_duration)
    max_empty_time = time_plus(fill_between[1], -min_fill_duration)
    max_full_time = fill_between[1]
    daily_start_fill = start_fill
    for d in date_range(start, end):
        daily_end_fill = daily_start_fill + buffer_storage_capacity
        min_empty_datetime = datetime.combine(d, min_empty_time)
        min_full_datetime = datetime.combine(d, min_full_time)
        max_empty_datetime = datetime.combine(d, max_empty_time)
        max_full_datetime = datetime.combine(d, max_full_time)
        day_start_datetime = d.replace(hour=0, minute=0, second=0).to_pydatetime()
        day_end_datetime = day_start_datetime + timedelta(days=1)
        df["max"].loc[day_start_datetime : min_empty_datetime - resolution] = daily_start_fill
        df["min"].loc[day_start_datetime : max_empty_datetime - resolution] = daily_start_fill
        for fill_step in range(min_fill_steps):

            # Fill max column forward from min_fill_datetime
            fill_max_value = daily_start_fill + (fill_step + 1) * buffer_power_capacity * resolution/timedelta(hours=1)
            df["max"].loc[min_empty_datetime - resolution + (fill_step + 1) * resolution] = fill_max_value

            # Fill min column backward from max_fill_datetime
            fill_min_value = daily_end_fill - (fill_step + 1) * buffer_power_capacity * resolution / timedelta(hours=1)
            df["min"].loc[max_full_datetime - resolution - (fill_step + 1) * resolution] = fill_min_value
        df["max"].loc[min_full_datetime - resolution : day_end_datetime] = daily_end_fill
        df["min"].loc[max_full_datetime - resolution : day_end_datetime] = daily_end_fill

        # Update for next day
        daily_start_fill = daily_end_fill
    # import pandas as pd
    # with pd.option_context("display.max_columns", None, "display.max_rows", None):
    #     input(df.loc[:, "max": "min"])
    return df
