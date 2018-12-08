from datetime import datetime, timedelta

from typing import Tuple

from pandas import DataFrame, Series, DatetimeIndex

from numpy import where, NaN

from comopt.model.utils import initialize_df

from numpy.random import uniform, randint, choice


def none_ever(start: datetime, end: datetime, resolution: timedelta) -> DataFrame:
    """No balancing opportunities ever."""

    return initialize_df(
        columns=["Imbalance (in MW)", "Price (in EUR/MWh)"],
        start=start,
        end=end,
        resolution=resolution,
    )


def single_curtailment_each_day_from_hours_a_to_b(
    start: datetime, end: datetime, resolution: timedelta, a: int, b: int
) -> DataFrame:
    """Each day it is valuable to curtail production from hours a to b (e.g. between 2 and 3 am)."""
    opportunity_start_time = "%s:00" % a
    opportunity_end_time = "%s:00" % b
    imbalance_value = 100  # MW
    imbalance_price_from_hours_a_to_b = 10  # EUR/MWh
    df = initialize_df(
        columns=["Imbalance (in MW)", "Price (in EUR/MWh)"],
        start=start,
        end=end,
        resolution=resolution,
    )
    df["Imbalance (in MW)"].iloc[
        df.index.indexer_between_time(
            start_time=opportunity_start_time,
            end_time=opportunity_end_time,
            include_end=False,
        )
    ] = imbalance_value
    df["Price (in EUR/MWh)"].iloc[
        df.index.indexer_between_time(
            start_time=opportunity_start_time,
            end_time=opportunity_end_time,
            include_end=False,
        )
    ] = imbalance_price_from_hours_a_to_b
    return df


def single_curtailment_or_shift_each_day_from_hours_a_to_b(
    start: datetime, end: datetime, resolution: timedelta, a: int, b: int
) -> DataFrame:
    """Each day it is valuable to curtail production from hours a to b (e.g. between 2 and 3 am),
    or to shift consumption to that period."""
    imbalance_start_time = "%s:00" % a
    imbalance_end_time = "%s:00" % b
    imbalance_value = 2  # MW
    imbalance_price_from_hours_a_to_b = 10  # EUR/MWh
    imbalance_price_otherwise = 5  # EUR/MWh
    df = initialize_df(
        columns=["Imbalance (in MW)", "Price (in EUR/MWh)"],
        start=start,
        end=end,
        resolution=resolution,
    )
    df["Imbalance (in MW)"] = 0
    df["Imbalance (in MW)"].iloc[
        df.index.indexer_between_time(
            start_time=imbalance_start_time,
            end_time=imbalance_end_time,
            include_end=False,
        )
    ] = imbalance_value
    df["Price (in EUR/MWh)"] = imbalance_price_otherwise
    df["Price (in EUR/MWh)"].iloc[
        df.index.indexer_between_time(
            start_time=imbalance_start_time,
            end_time=imbalance_end_time,
            include_end=False,
        )
    ] = imbalance_price_from_hours_a_to_b
    return df


def generated_imbalance_profile(
    start: datetime,
    end: datetime,
    resolution: timedelta,
    imbalance_range: Tuple,
    imbalance_price_1: float,
    imbalance_price_2: float,
    frequency: float,
    window_size: Tuple,
    imbalance_profile: Series = None,
    imbalance_prices: Series = None,
) -> DataFrame:
    """Generate imbalances for a given timeperiod."""

    df = initialize_df(
        columns=["Imbalance (in MW)", "Price (in EUR/MWh)"],
        start=start,
        end=end,
        resolution=resolution,
    )

    if imbalance_profile is None:
        dummy_index = DatetimeIndex(start=start, end=end, freq=resolution)
        num_samples = int(len(dummy_index) * frequency)
        windows_data = uniform(size=len(dummy_index))
        windows = Series(data=windows_data, index=dummy_index)
        samples_df = Series(index=dummy_index)
        samples = [
            windows.iloc[x : x + randint(window_size[0], window_size[1])]
            * choice([-1, 1])
            for x in randint(len(windows), size=num_samples)
        ]

        for sample in samples:
            samples_df.loc[sample.index[0] : sample.index[-1]] = sample

        samples_df[samples_df < 0] = samples_df[samples_df < 0] * imbalance_range[0]
        samples_df[samples_df > 0] = samples_df[samples_df > 0] * imbalance_range[1]
        imbalance_profile = samples_df

        df["Imbalance (in MW)"] = 0
        df["Imbalance (in MW)"].loc[start:end] = imbalance_profile.loc[start:end]
        df["Price (in EUR/MWh)"] = where(
            df["Imbalance (in MW)"] == NaN, imbalance_price_1, imbalance_price_2
        )
    else:
        df["Imbalance (in MW)"].loc[start:end] = imbalance_profile
        df["Price (in EUR/MWh)"] = imbalance_prices
        # print("balance")
        # print(df)

    return df
