# Ideas for profile generators

from datetime import datetime, timedelta

import more_itertools as mit
from comopt.model.utils import initialize_df, initialize_index
from typing import Dict, List, Tuple
import enlopy as el

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pandas import DataFrame, Series
from datetime import datetime, timedelta
import random
import pickle
from copy import deepcopy
import enlopy


# def create_nonshiftable_load_profiles(data: DataFrame = None) -> DataFrame:
#     start = data.index.get_level_values(level="datetime").unique()[0]
#     end = data.index.get_level_values(level="datetime").unique()[-1]
#
#     full_year_monthly_profile = (np.cos(2 * np.pi/12 * np.linspace(0,11,12)) * 50 + 100 ) * 0.75
#     full_year_monthly_load_profile = el.make_timeseries(full_year_monthly_profile)
#
#     dummy_index = pd.DatetimeIndex(start=datetime(year=2018, month=1, day=1),
#                                    end=datetime(year=2019, month=1, day=1, hour=0),
#                                    freq="H")
#     dummy_index = dummy_index.drop(dummy_index[-1])
#
#     for ems in data.index.get_level_values(level="ems").unique():
#         for device in data.index.get_level_values(level="device").unique():
#             if ems in device and "Nonshiftable_Load" in device:
#                 # energy will be split in working day and non working day by weight variable
#                 weight = random.uniform(0.5, 0.8)
#                 daily_load_working = el.gen_daily_stoch_el()
#                 daily_load_non_working = el.gen_daily_stoch_el()
#                 profile = el.gen_load_from_daily_monthly(full_year_monthly_load_profile, daily_load_working,
#                                                          daily_load_non_working, weight)
#
#                 profile_noized = el.add_noise(profile, 1, 0.35)
#                 profile_noized.index = dummy_index
#                 profile_noized = profile_noized.drop(index=profile_noized.index[-1]).resample(rule="15T").mean()
#                 profile_noized = profile_noized.interpolate(method='linear').drop(index=profile_noized.index[-1])
#                 data.loc[idx[:,ems, device],"Derivative_Equal"] = profile_noized[start:end].values
#     return data
#
# def create_buffer_profiles(data: DataFrame, buffer_charging_limits: Dict,
#                            frequency: float, window_length: Tuple) -> DataFrame:
#
#     datetime_index = data.index.get_level_values(level="datetime").unique()
#     start = data.index.get_level_values(level="datetime").unique()[0]
#     end = data.index.get_level_values(level="datetime").unique()[-1]
#
#     num_samples = int(len(datetime_index)*frequency)
#
#     for ems in data.index.get_level_values(level="ems").unique():
#         windows = pd.DataFrame(np.random.uniform(size=len(datetime_index))*0.25,
#                                index=datetime_index, columns=['vals'])
#         samples_df = pd.DataFrame(index=datetime_index, columns=["vals"])
#         for device in data.index.get_level_values(level="device").unique():
#             if ems in device and "Buffer" in device:
#                 samples = [windows.iloc[x:x+random.randint(window_length[0],window_length[1],)]
#                            for x in np.random.randint(len(windows), size=num_samples)]
#                 for sample in samples:
#                     sample_sum = sample.sum()
#                     samples_df.loc[sample.index[0]:sample.index[-1]] = round(sample_sum["vals"], 2)
#                 data.loc[idx[start:end, ems, device], "Integral_Equal"] = samples_df.values
#                 data.loc[idx[start:end, ems, device], "Derivative_Max"] = buffer_charging_limits["Max"]
#                 data.loc[idx[start:end, ems, device], "Derivative_Min"] = buffer_charging_limits["Min"]
#     return data
#
# def create_solar_profiles(data: DataFrame) -> DataFrame:
#
#     datetime_index = data.index.get_level_values(level="datetime").unique()
#     start = data.index.get_level_values(level="datetime").unique()[0]
#     end = data.index.get_level_values(level="datetime").unique()[-1]
#
#     b = pd.DatetimeIndex.indexer_between_time(start_time=start, end_time=end)
#     device_names = data.index.get_level_values(level="device").unique()
#     ems_names = data.index.get_level_values(level="ems").unique()
#
#     for ems in ems_names:
#         mu, sigma = 1, 0.01
#         s = np.random.normal(mu, sigma, 5000)
#         count, bins, ignored = plt.hist(s, 96, normed=False)
#         n = normalize(count)
#         for device in device_names:
#             if ems in device and "Nonshiftable_Generator" device:
#                 n=n*(1+random.uniform(-0.125,0.2))
#                 data.loc[idx[:, ems, device], "Integral_Equal"] = samples_df.values
#     return #data

def pickle_profiles(start: datetime, end: datetime, resolution: timedelta):

    # Pickle profile data
    pickle_off = open("../comopt/pickles/imbalances_test_profile_1_day.pickle","rb")
    imbalances_test_profile_1_day = pickle.load(pickle_off)
    # imbalances_test_profile_1_day *= 2
    # imbalances_test_profile_1_day = abs(imbalances_test_profile_1_day)

    # i = deepcopy(imbalances_test_profile_1_day[start:end])
    # i[start:end] = 2
    # # i[1] *=-1
    # i[2] *=-1
    # i[4:] = 0
    # imbalances_test_profile_1_day = deepcopy(i)

    pickle_off = open("../comopt/pickles/imbalance_prices_test_profile_1_day.pickle","rb")
    imbalance_prices_test_profile_1_day = pickle.load(pickle_off)
    imbalance_prices_test_profile_1_day = 6.5

    pickle_off = open("../comopt/pickles/solar_test_profile_1_day.pickle","rb")
    solar_test_profile_1_day = pickle.load(pickle_off)
    # solar_test_profile_1_day.loc[:] = 3
    solar_test_profile_1_day=round(solar_test_profile_1_day,1)

    pickle_off = open("../comopt/pickles/load_test_profile_1_day.pickle","rb")
    load_test_profile_1_day = pickle.load(pickle_off)
    # load_test_profile_1_day.loc[:] = 6
    load_test_profile_1_day=round(load_test_profile_1_day,1)

    pickle_off = open("../comopt/pickles/deviation_prices_1_day.pickle","rb")
    deviation_prices = pickle.load(pickle_off)
    # load_test_profile_1_day.loc[:] = 6

    # Prices & Costs
    purchase_price = 32
    feed_in_price = 20
    dev_base_price = (purchase_price + feed_in_price)/2

    imbalance_market_costs = abs(imbalances_test_profile_1_day) * imbalance_prices_test_profile_1_day
    imbalance_market_costs_normalized = imbalance_market_costs/max(imbalance_market_costs)

    ## opt 2
    # deviation_prices = imbalance_market_costs_normalized
    deviation_prices[:] = 30

    activated_load = enlopy.generate.gen_demand_response(load_test_profile_1_day,
                                                          percent_peak_hrs_month=0.33,
                                                          percent_shifted=0.25, shave=False)
    flexible_load_profile = DataFrame(index=load_test_profile_1_day.index, columns=["derivative min", "derivative max"])

    # for idx in flexible_load_profile.index:
    #     flexible_load_profile.loc[idx,"derivative min"] = min(activated_load[idx],load_test_profile_1_day[idx])
    #     flexible_load_profile.loc[idx,"derivative max"] = max(activated_load[idx],load_test_profile_1_day[idx])

    for idx in flexible_load_profile.index:
        flexible_load_profile.loc[idx,"derivative min"] = 0
        # flexible_load_profile.loc["2018-06-01 08:15:00","derivative min"]  = 0
        # flexible_load_profile.loc["2018-06-01 09:00:00":,"derivative min"]  = 0

        flexible_load_profile.loc[idx,"derivative max"] = 2
        # flexible_load_profile.loc["2018-06-01 08:15:00","derivative max"]  = 0
        # flexible_load_profile.loc["2018-06-01 09:00:00":,"derivative max"]  = 0

    # solar_test_profile_1_day.loc["2018-06-01 08:00:00"]  = 0
    # solar_test_profile_1_day.loc["2018-06-01 08:15:00"]  = 2
    # solar_test_profile_1_day.loc["2018-06-01 08:30:00"]  = 2
    # solar_test_profile_1_day.loc["2018-06-01 08:45:00"]  = 4
    # solar_test_profile_1_day.loc["2018-06-01 09:00:00":]  = 0

    net_demand_without_flex = flexible_load_profile.loc[:,"derivative min"] - solar_test_profile_1_day
    net_demand_costs_without_flex = deepcopy(net_demand_without_flex)
    net_demand_costs_without_flex[net_demand_costs_without_flex>0] = net_demand_costs_without_flex[net_demand_costs_without_flex>0]*purchase_price
    net_demand_costs_without_flex[net_demand_costs_without_flex<0] = net_demand_costs_without_flex[net_demand_costs_without_flex<0]*feed_in_price

    return {"imbalances_test_profile_1_day":imbalances_test_profile_1_day, \
            "imbalance_prices_test_profile_1_day":imbalance_prices_test_profile_1_day, \
            "solar_test_profile_1_day": solar_test_profile_1_day, \
            "load_test_profile_1_day": load_test_profile_1_day, \
            "deviation_prices": deviation_prices, \
            "purchase_price": purchase_price, \
            "feed_in_price": feed_in_price, \
            "imbalance_market_costs": imbalance_market_costs, \
            "flexible_load_profile": flexible_load_profile, \
            "net_demand_without_flex": net_demand_without_flex, \
            "net_demand_costs_without_flex":net_demand_costs_without_flex}


# idx = initialize_index(start=start_day, end=end_day, resolution=resolution_day)
# imbalances_test_profile_1_day = enlopy.generate.gen_daily_stoch_el(total_energy=10.0)
# i = enlopy.generate.gen_gauss_markov(imbalances_test_profile_1_day,2,r=0.7)
# i = Series(index=idx, data=i)
# # i["2018-06-02 00:00:00"] = 2.2445
# i = i.resample(rule="15T")
# i = i.interpolate(method='nearest')
# i["2018-06-01 00:00:00"] = 0
# i["2018-06-01 23:15:00"] = 1.233
# i["2018-06-01 23:30:00"] = 0.878
# i["2018-06-01 23:45:00"] = 0.278
#
# # plt.plot(i)
# p = deepcopy(i)
# y = idx[0]
# for x in idx:
#     if x != idx[-1]:
#         i[x] = i[x] * gauss(uniform(0,5),uniform(-0.5,0.5)) * 0.5 + uniform(-0.25,0.25)*0.5
#         p[x] = i[x]*0.5 + i[y] * gauss(0,uniform(-1,1)) *0.5
#         seed()
#     else:
#         pass
#     y=x
#
# imbalances_test_profile_1_day = i
# imbalance_prices_test_profile_1_day = p
# plt.plot(i)
# plt.plot(abs(p))

# pickling_on = open("imbalances_test_profile_1_day.pickle","wb")
# pickle.dump(imbalances_test_profile_1_day, pickling_on)
# pickling_on.close()
#
# pickling_on = open("imbalance_prices_test_profile_1_day.pickle","wb")
# pickle.dump(abs(p), pickling_on)
# pickling_on.close()

# pickling_on = open("curtailable_solar_test_profile_1_day.pickle","wb")
# pickle.dump(curtailable_solar_test_profile_1_day, pickling_on)
# pickling_on.close()

# pickling_on = open("dispatchable_load_test_profile_1_day.pickle","wb")
# pickle.dump(dispatchable_load_test_profile_1_day, pickling_on)
# pickling_on.close()

# start_day = datetime(year=2018, month=6, day=1, hour=0)
# end_day = datetime(year=2018, month=6, day=2, hour=0)
# resolution_day = timedelta(hours=1)

# imbalance_market_costs_normalized[:] = 10
#deviation_prices = imbalance_market_costs_normalized
# deviation_multiplicator = 1
# # env.ems_agents[0].flex_per_device[]
#
# #geometric_growing_deviation_prices = [1.8**x for x in range(8,8+len(imbalances_test_profile_1_day.index))]
# deviation_prices = Series(index=imbalances_test_profile_1_day.index, data=imbalance_prices_test_profile_1_day)
# #deviation_prices = imbalance_market_costs_normalized
# # deviation_prices[deviation_prices>0.20] = 1000
# # deviation_prices.plot()
# for x in deviation_prices.index:
#     if deviation_prices[x] > 0.2:
#         deviation_prices[x] = deviation_prices[x] + (uniform(0,100))
#
# # deviation_prices.plot()
# # imbalance_prices_test_profile_1_day *= 10
# deviation_prices

#------------------------------- PLOTTRY ----------------------------------------------------#
# cut_off_indices = int(env.max_horizon/resolution - 1)
# index = env.simulation_runtime_index[:-cut_off_indices]
# from pandas import Index
# ta_horizon_periods = int(env.trading_agent.prognosis_horizon/resolution)+1
# start = 1
# horizons_index = Index([x for x in range(1,ta_horizon_periods+1)])
# horizons_index
# horizon_costs=env.ems_agents[0].planned_costs_over_horizons
#
# triangle_horizons = DataFrame(index=index, columns=horizons_index)
# triangle_horizons
# # planned_costs = Series(index=index, data=[sum(ems.planned_costs_over_horizons[idx]) for idx in ems.planned_costs_over_horizons])
# # planned_costs_horizons = DataFrame(index=index, columns=index)
# for idx in triangle_horizons.index:
#     cnt = 0
#     for enum, col in enumerate(triangle_horizons.columns):
#         # reverse_horizon = ta_horizon_periods - enum - 1
#         # print(row)
#         try:
#             # horizon_costs[idx].reverse()
#             triangle_horizons.loc[idx, col] = horizon_costs[idx][enum]
#         except:
#             pass
#
# resorted_columns=list(range(1,ta_horizon_periods+1))
# resorted_columns.reverse()
# triangle_horizons.rename(columns=dict(zip(horizons_index, resorted_columns)),inplace=True)
# triangle_horizons.reset_index(inplace=True)
# for colnum,col  in enumerate(triangle_horizons.columns):
#     for enum,index in enumerate(triangle_horizons.index):
#         if colnum == 0:
#             pass
#         else:
#             plt.plot(triangle_horizons.iloc[index][0], colnum, marker='.', linestyle='solid', linewidth=2,
#                     markersize=triangle_horizons.iloc[index,colnum])
#
# plt.show()
#
# triangle_horizons.plot.scatter(x=triangle_horizons["datetime"],y=triangle_horizons[5])
# triangle_horizons.T.reindex([5,4,3,2,1]).plot()
# triangle_horizons.T.plot(index=triangle_horizons.index,legend=False)
# plt.plot(triangle_horizons[1], facecolors='b')


## TOY EXAMPLE INPUTSabs
    # Pickle profile data
    # pickle_off = open("../comopt/pickles/imbalances_test_profile_1_day.pickle","rb")
    # imbalances_test_profile_1_day = pickle.load(pickle_off)
    # imbalances_test_profile_1_day *= 2
    # imbalances_test_profile_1_day = abs(imbalances_test_profile_1_day)
    #
    # i = deepcopy(imbalances_test_profile_1_day[start:end])
    # i[start:end] = 2
    # # i[1] *=-1
    # i[2] *=-1
    # i[4:] = 0
    # imbalances_test_profile_1_day = deepcopy(i)
    #
    # pickle_off = open("../comopt/pickles/imbalance_prices_test_profile_1_day.pickle","rb")
    # imbalance_prices_test_profile_1_day = pickle.load(pickle_off)
    # imbalance_prices_test_profile_1_day = 6.5
    #
    # pickle_off = open("../comopt/pickles/solar_test_profile_1_day.pickle","rb")
    # solar_test_profile_1_day = pickle.load(pickle_off)
    # # solar_test_profile_1_day.loc[:] = 3
    # solar_test_profile_1_day=round(solar_test_profile_1_day,1)
    #
    # pickle_off = open("../comopt/pickles/load_test_profile_1_day.pickle","rb")
    # load_test_profile_1_day = pickle.load(pickle_off)
    # # load_test_profile_1_day.loc[:] = 6
    # load_test_profile_1_day=round(load_test_profile_1_day,1)
    #
    # pickle_off = open("../comopt/pickles/deviation_prices_1_day.pickle","rb")
    # deviation_prices = pickle.load(pickle_off)
    # # load_test_profile_1_day.loc[:] = 6
    #
    # # Prices & Costs
    # purchase_price = 32
    # feed_in_price = 20
    # dev_base_price = (purchase_price + feed_in_price)/2
    #
    # imbalance_market_costs = abs(imbalances_test_profile_1_day) * imbalance_prices_test_profile_1_day
    # imbalance_market_costs_normalized = imbalance_market_costs/max(imbalance_market_costs)
    #
    # ## opt 2
    # deviation_prices = imbalance_market_costs_normalized
    # deviation_prices[:] = 30
    #
    # activated_load = enlopy.generate.gen_demand_response(load_test_profile_1_day,
    #                                                       percent_peak_hrs_month=0.33,
    #                                                       percent_shifted=0.25, shave=False)
    # flexible_load_profile = DataFrame(index=load_test_profile_1_day.index, columns=["derivative min", "derivative max"])
    #
    # # for idx in flexible_load_profile.index:
    # #     flexible_load_profile.loc[idx,"derivative min"] = min(activated_load[idx],load_test_profile_1_day[idx])
    # #     flexible_load_profile.loc[idx,"derivative max"] = max(activated_load[idx],load_test_profile_1_day[idx])
    #
    # for idx in flexible_load_profile.index:
    #     flexible_load_profile.loc[idx,"derivative min"] = 2
    #     flexible_load_profile.loc["2018-06-01 08:15:00","derivative min"]  = 0
    #     flexible_load_profile.loc["2018-06-01 09:00:00":,"derivative min"]  = 0
    #
    #     flexible_load_profile.loc[idx,"derivative max"] = 2
    #     flexible_load_profile.loc["2018-06-01 08:15:00","derivative max"]  = 0
    #     flexible_load_profile.loc["2018-06-01 09:00:00":,"derivative max"]  = 0
    #
    # solar_test_profile_1_day.loc["2018-06-01 08:00:00"]  = 0
    # solar_test_profile_1_day.loc["2018-06-01 08:15:00"]  = 2
    # solar_test_profile_1_day.loc["2018-06-01 08:30:00"]  = 2
    # solar_test_profile_1_day.loc["2018-06-01 08:45:00"]  = 4
    # solar_test_profile_1_day.loc["2018-06-01 09:00:00":]  = 0
    #
    # net_demand_without_flex = flexible_load_profile.loc[:,"derivative min"] - solar_test_profile_1_day
    # net_demand_costs_without_flex = deepcopy(net_demand_without_flex)
    # net_demand_costs_without_flex[net_demand_costs_without_flex>0] = net_demand_costs_without_flex[net_demand_costs_without_flex>0]*purchase_price
    # net_demand_costs_without_flex[net_demand_costs_without_flex<0] = net_demand_costs_without_flex[net_demand_costs_without_flex<0]*feed_in_price
    #
    # return {"imbalances_test_profile_1_day":imbalances_test_profile_1_day, \
    #         "imbalance_prices_test_profile_1_day":imbalance_prices_test_profile_1_day, \
    #         "solar_test_profile_1_day": solar_test_profile_1_day, \
    #         "load_test_profile_1_day": load_test_profile_1_day, \
    #         "deviation_prices": deviation_prices, \
    #         "purchase_price": purchase_price, \
    #         "feed_in_price": feed_in_price, \
    #         "imbalance_market_costs": imbalance_market_costs, \
    #         "flexible_load_profile": flexible_load_profile, \
    #         "net_demand_without_flex": net_demand_without_flex, \
    #         "net_demand_costs_without_flex":net_demand_costs_without_flex}
