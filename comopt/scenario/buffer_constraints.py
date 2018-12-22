from datetime import datetime, timedelta
from typing import Tuple
from numpy.random import uniform, randint
from numpy import isnan, nan

from pandas import DataFrame, DatetimeIndex, Series, isnull

from comopt.scenario.ems_constraints import completely_unconstrained_profile

from comopt.model.utils import (
    initialize_series, initialize_index
)

from random import random

def follow_generated_buffer_profile(
    start: datetime,
    end: datetime,
    resolution: timedelta,
    buffer_power_capacity: float,
    fraction: float
) -> DataFrame:

    df = completely_unconstrained_profile(start=start, end=end, resolution=resolution)
    # df["equals"] = 0
    # df["derivative max"] = 0
    for index in df.sample(frac=fraction).index:
        df.loc[index:index+timedelta(minutes=resolution.seconds/60)*randint(1,3),"min"] \
            = round(uniform(1,buffer_power_capacity))

    for index in df.loc[df['min'] > 0].index:
        df.loc[index, 'derivative max'] = buffer_power_capacity
        df.loc[index, "derivative min"] = 0


    df.iloc[-1] = nan

    #TODO: Improve sorting loop
    last_index = None
    sum = 0
    num = nan
    for index, row in df['min'].iteritems():

        if not isnull(row):
            sum += row
            num = row
            last_index = index
            last_value=row
            df.loc[last_index,'min'] = nan

        if num != row:
            df.loc[last_index,'min'] = sum
            sum = 0
            num = row
            last_index = index

    df['min'].loc[df["min"] == 0] = nan#
    # df["max"] = df["min"]

    print(df.loc[start:end-resolution,:])

    return df.loc[start:end-resolution,:]
#     else:
#         df.loc[index,'min'] = sum
# #     if not isnull(last_value):
#         df.loc[index,'min'] = nan
#         if row != num:
#             num = row
#             print(num)
#     last_value = row


# df.plot(df["min"])

# %%

# def limited_buffer_capacity_profile(
#     start: datetime,
#     end: datetime,
#     resolution: timedelta,
#     buffer_power_capacity: float,
# ) -> DataFrame:
#     df = completely_unconstrained_profile(start=start, end=end, resolution=resolution)
#     df["derivative max"] = buffer_power_capacity
#     df["derivative min"] = -buffer_power_capacity
#     df["min"] = soc_limits[0]
#     df["max"] = soc_limits[1]
#     df["equals"].iloc[0] = soc_start
#     return df


# def follow_generated_buffer_profile(
#     start: datetime,
#     end: datetime,
#     resolution: timedelta,
#     buffer_power_capacity: float,
#     frequency: float,
#     window_size: float,
# ) -> DataFrame:
#     df = completely_unconstrained_profile(start=start, end=end, resolution=resolution)
#     df["derivative max"] = buffer_power_capacity
#     # df["derivative min"] = -buffer_power_capacity
#     # # df["min"] = soc_limits[0]
#     # # df["max"] = soc_limits[1]
#     # # df["equals"].iloc[0] = soc_start
#     #
#     dummy_index = initialize_index(start=start, end=end, freq=resolution)
#     num_samples = int(len(dummy_index) * frequency)
#
#     windows_data = uniform(size=len(dummy_index))
#     windows = Series(data=windows_data * 5, index=dummy_index)
#     windows = round(windows,0)
#     samples_df = Series(index=dummy_index)
#     window_size = (2, 5)
#     samples = [
#         windows.iloc[x : x + randint(window_size[0], window_size[1])]
#         for x in randint(len(windows), size=num_samples)
#     ]
#
#     for sample in samples:
#         sample_sum = sample.sum()
#         samples_df.loc[sample.index[0] : sample.index[-1]] = sample_sum
#
#     # Catch and delete single windows
#     cnt = 0
#     last = samples_df.iloc[0]
#     for val in samples_df:
#         if isnan(val):
#             cnt += 1
#             last = val
#             continue
#         else:
#             if cnt == 0:
#                 cnt += 1
#                 continue
#             else:
#                 try:
#                     samples_df.iloc[cnt + 1]
#                 except:
#                     continue
#                 else:
#                     if last != val and samples_df.iloc[cnt + 1] != val:
#                         samples_df.iloc[cnt] = nan
#                         cnt += 1
#                         last = val
#                     else:
#                         cnt += 1
#                         last = val
#
#     df["min"] = 0
#     # df["derivative min"].iloc[-4:-1] = 0
#     # df["derivative max"].iloc[-4:-1] = 0
#     print(df)
#     return df
