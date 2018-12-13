from typing import List, Optional, Union, Callable, Tuple
from datetime import date, datetime, timedelta

from pandas import DataFrame, DatetimeIndex, Series, MultiIndex, Index
from pandas.tseries.frequencies import to_offset

from numpy import ndarray


def initialize_df(
    columns: List[str], start: datetime, end: datetime, resolution: timedelta
) -> DataFrame:
    df = DataFrame(index=initialize_index(start, end, resolution), columns=columns)
    return df


def initialize_series(
    data: Optional[Union[Series, List[float], ndarray, float]],
    start: datetime,
    end: datetime,
    resolution: timedelta,
) -> Series:
    s = Series(index=initialize_index(start, end, resolution), data=data)
    return s


def initialize_index(
    start: Union[date, datetime], end: Union[date, datetime], resolution: timedelta
) -> Series:
    i = DatetimeIndex(
        start=start, end=end, freq=to_offset(resolution), closed="left", name="datetime"
    )
    return i


def create_data_log(
    first_index: Union[List, Index],
    second_index: Union[List, Index],
    index_names: List,
    column_names: List) -> DataFrame:

    """ Returns a multiindex dataframe with inidices (datetime, rounds) and columns for prices, bids, profits, etc. """

    logfile = DataFrame(
        index=MultiIndex.from_product(
            iterables=[
                first_index,
                second_index,
            ],
            names=index_names,
        ),
        columns=column_names
    )
    return logfile
