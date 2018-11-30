from datetime import datetime, timedelta
from typing import Tuple
import enlopy as el
from random import uniform
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
from pandas import DataFrame, Series, DatetimeIndex, RangeIndex
from numpy import nan, cos, pi, linspace
from numpy.random import normal
from matplotlib.pyplot import hist
from comopt.model.utils import initialize_df, initialize_index


# Todo: add functions for round-trip efficiency losses and dissipation losses over time
def completely_unconstrained_profile(
    start: datetime, end: datetime, resolution: timedelta
) -> DataFrame:
    """Can be used as a base model."""
    return initialize_df(
        columns=[
            "equals",
            "max",
            "min",
            "derivative equals",
            "derivative max",
            "derivative min",
        ],
        start=start,
        end=end,
        resolution=resolution,
    )

def limited_capacity_profile(
    start: datetime, end: datetime, resolution: timedelta, capacity: float
) -> DataFrame:
    """Can be used to model a prosumer or a battery with unlimited storage capacity."""
    df = completely_unconstrained_profile(start=start, end=end, resolution=resolution)
    df["derivative max"] = capacity
    df["derivative min"] = -capacity
    return df


def limited_production_profile(
    start: datetime, end: datetime, resolution: timedelta, capacity: float
) -> DataFrame:
    """Can be used to model a generator."""
    df = limited_capacity_profile(
        start=start, end=end, resolution=resolution, capacity=capacity
    )
    df["derivative max"] = 0
    return df


def limited_consumption_profile(
    start: datetime, end: datetime, resolution: timedelta, capacity: float
) -> DataFrame:
    """Can be used to model a consumer without distributed generation."""
    df = limited_capacity_profile(
        start=start, end=end, resolution=resolution, capacity=capacity
    )
    df["derivative min"] = 0
    return df

def dispatchable_load_profile_with_bounds(
    start: datetime, end: datetime, resolution: timedelta, profile: DataFrame,
) -> DataFrame:

    """Can be used to model a consumer with flexible load profile."""
    df = limited_capacity_profile(
        start=start, end=end, resolution=resolution, capacity=profile["derivative min"].max()
    )
    df["derivative min"] = profile.loc[:,"derivative min"]
    df["derivative max"] = profile.loc[:,"derivative max"]

    return df


def follow_generated_consumption_profile(
    start: datetime, end: datetime, resolution: timedelta, max_capacity: float, dispatch_factor: float = None, profile: Series = None) -> DataFrame:
    """Can be used to model a device with the artificially generatred consumption or production profiles."""

    if profile is None:
        full_year_monthly_profile = (cos(2 * pi/12 * linspace(0,11,12)) * 50 + 100 ) * 0.75
        full_year_monthly_load_profile = el.make_timeseries(full_year_monthly_profile)
        dummy_index = DatetimeIndex(start=datetime(year=2018, month=1, day=1),
                                    end=datetime(year=2019, month=1, day=1, hour=0),
                                    freq="H")
        dummy_index = dummy_index.drop(dummy_index[-1])

        weight = uniform(0.5, 0.8)
        daily_load_working = el.gen_daily_stoch_el()
        daily_load_non_working = el.gen_daily_stoch_el()
        profile = el.gen_load_from_daily_monthly(full_year_monthly_load_profile, daily_load_working, daily_load_non_working, weight)
        profile_noized = el.add_noise(profile, 3, 0.25)
        profile_noized.index = dummy_index

        if int(resolution.seconds/3600) == 1.0:
            pass
        else:
            profile_noized = profile_noized.drop(index=profile_noized.index[-1]).resample(rule="15T").mean()
            profile_noized = profile_noized.interpolate(method='linear').drop(index=profile_noized.index[-1])
            profile_noized = profile_noized + abs(normal(0, 0.05, [len(profile_noized.index)]))
        profile = profile_noized * max_capacity

    else:
        pass

    df = limited_consumption_profile(
        start=start, end=end, resolution=resolution, capacity=max_capacity)

    df["derivative equals"] = profile.loc[start : end-resolution].values

    if dispatch_factor is not None:
        if dispatch_factor == 0:
            pass

        if dispatch_factor == 1:
            df["derivative max"] = df["derivative equals"]
            df["derivative equals"] = nan

        else:
            df["derivative max"] = df["derivative equals"]
            df["derivative equals"] = df["derivative equals"] * (1-dispatch_factor)
            # print(df)
            # print("consumption")
    return df

def follow_generated_production_profile(
    start: datetime, end: datetime, resolution: timedelta, max_capacity: float, dispatch_factor: float = None, profile: Series = None) -> DataFrame:

    if profile is None:
        dummy_index = DatetimeIndex(start=datetime(year=2018, month=1, day=1),
                                    end=datetime(year=2019, month=1, day=1, hour=0),
                                    freq="15T")
        dummy_index = dummy_index.drop(dummy_index[-96])

        mu, sigma = 1, 0.01
        s = normal(mu, sigma, 5000)
        count, bins, ignored = hist(s, 72, normed=False)
        daily_profile = count/count.max()
        yearly_curve = (-cos(2 * pi/35040 * linspace(0,35039,35040) + 0.2) * 50 + 100) * 0.75

        stacks = []

        for i in range(1,366):
            s = Series(index=RangeIndex(start=1, stop=97, step=1), data=0)
            s[12:84] = el.add_noise(daily_profile, mode=3, st=0.05, Lmin=0, r=0.01).values
            stacks.append(list(s.values))

        stacks = [item for sublist in stacks for item in sublist]
        full_year_profile = stacks * yearly_curve
        full_year_profile= full_year_profile/full_year_profile.max()
        profile = Series(data=full_year_profile, index=dummy_index)
        profile *= max_capacity
    else:
        pass

    df = limited_production_profile(
        start=start, end=end, resolution=resolution, capacity=max_capacity)
    df["derivative equals"] = -profile.loc[start : end-resolution].values

    if dispatch_factor is not None:
        if dispatch_factor == 0:
            pass

        if dispatch_factor == 1:
            df["derivative min"] = df["derivative equals"]
            df["derivative equals"] = nan

        else:
            df["derivative min"] = df["derivative equals"]
            df["derivative equals"] = df["derivative equals"] * (1-dispatch_factor)
            # print("generation")
            # print(df)
    return df

def follow_daily_profile(
    start: datetime, end: datetime, resolution: timedelta, daily_power, production=False
) -> DataFrame:
    """Can be used to model a device with the same consumption or production profile every day.
    daily_power should contain positive values."""

    max_capacity = max(daily_power)
    n_days = (end.date() - start.date() + timedelta(days=1)).days
    s = Series(
        data=daily_power * n_days,
        index=initialize_index(
            start.date(), end.date() + timedelta(days=1), timedelta(hours=1)
        ),
    )
    ix = initialize_index(start.date(), end.date() + timedelta(days=1), resolution)
    s = s.resample(ix.freqstr).pad()

    if production is True:
        df = limited_production_profile(
            start=start, end=end, resolution=resolution, capacity=max_capacity
        )
        df["derivative equals"] = -s.loc[start : end - resolution].values
    else:
        df = limited_consumption_profile(
            start=start, end=end, resolution=resolution, capacity=max_capacity
        )
        df["derivative equals"] = s.loc[start : end - resolution].values

    return df


def follow_solar_profile(
    start: datetime, end: datetime, resolution: timedelta
) -> DataFrame:
    """Can be used to model a solar panel with the same generation profile every day."""

    daily_power = [
        0,
        0,
        0,
        0,
        0,
        0,
        0.006362672,
        0.039236479,
        0.067868505,
        0.100742312,
        0.117709438,
        0.130434783,
        0.102863203,
        0.092258749,
        0.083775186,
        0.086956522,
        0.06892895,
        0.058324496,
        0.033934252,
        0.010604454,
        0,
        0,
        0,
        0,
    ]

    return follow_daily_profile(start, end, resolution, daily_power, production=True)


def curtailable_solar_profile(
    start: datetime, end: datetime, resolution: timedelta
) -> DataFrame:
    """Can be used to model a fully curtailable solar panel with the same generation profile every day."""

    df = follow_solar_profile(
        start=start, end=end, resolution=resolution
    )
    df["derivative min"] = df["derivative equals"]
    df["derivative equals"] = nan

    return df

def curtailable_integer_solar_profile(
    start: datetime, end: datetime, resolution: timedelta
) -> DataFrame:
    """Can be used to model a fully curtailable solar panel with the same generation profile every day."""

    daily_power = list(range(24))

    df = follow_daily_profile(start, end, resolution, daily_power, production=True)
    df["derivative min"] = df["derivative equals"]
    df["derivative equals"] = nan

    return df

def follow_integer_test_profile(
    start: datetime, end: datetime, resolution: timedelta
) -> DataFrame:
    """Models a test load profile that repeats every day, with incrementally increasing integer values."""

    daily_power = list(range(24))

    return follow_daily_profile(start, end, resolution, daily_power)


# def create_solar_profiles(start: datetime, end: datetime, resolution: timedelta
# ) -> DataFrame:
#
#     mu, sigma = 1, 0.01
#     s = np.random.normal(mu, sigma, 5000)
#     count, bins, ignored = plt.hist(s, 48, normed=False)
#     profile = count/count.max()*(1+uniform(-0.125,0.2))
#
#     df = limited_consumption_profile(
#         start=start, end=end, resolution=resolution, capacity=max_capacity
#     )
#     df["derivative equals"] = s.loc[start : end - resolution].values
#
#     data.loc[idx[:, ems, device], "Integral_Equal"] = samples_df.values
#
#     return #data
