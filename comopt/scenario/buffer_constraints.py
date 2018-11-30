from datetime import datetime, timedelta
from typing import Tuple

from pandas import DataFrame

from comopt.model.ems_constraints import completely_unconstrained_profile


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

def follow_generated_buffer_profile(
    start: datetime,
    end: datetime,
    resolution: timedelta,
    buffer_power_capacity: float,
    frequency: float,
    window_size: float,
) -> DataFrame:
    df = completely_unconstrained_profile(start=start, end=end, resolution=resolution)
    df["derivative max"] = buffer_power_capacity
    df["derivative min"] = -buffer_power_capacity
    df["min"] = soc_limits[0]
    df["max"] = soc_limits[1]
    df["equals"].iloc[0] = soc_start

    dummy_index = DatetimeIndex(start=start, end=end, freq=resolution)
    num_samples = int(len(dummy_index)*frequency)

    windows_data=uniform(size=len(dummy_index))*0.25
    windows = Series(data=windows_data*0.25,
                     index=dummy_index)

    samples_df = Series(index=dummy_index)
    window_size = (2,5)
    samples = [windows.iloc[x:x+randint(window_size[0],window_size[1],)]
               for x in randint(len(windows), size=num_samples)]

    for sample in samples:
        sample_sum = sample.sum()
        samples_df.loc[sample.index[0]:sample.index[-1]] = sample_sum

    # Catch and delete single windows
    cnt = 0
    last = samples_df.iloc[1]
    for val in samples_df:
        if isnan(val):
            cnt += 1
            last = val
            continue
        else:
            if cnt == 0:
                cnt += 1
                continue
            else:
                try:
                    samples_df.iloc[cnt+1]
                except:
                    continue
                else:
                    if last != val and samples_df.iloc[cnt+1] != val:
                        samples_df.iloc[cnt] = nan
                        cnt += 1
                        last = val
                    else:
                        cnt += 1
                        last = val

    return df
