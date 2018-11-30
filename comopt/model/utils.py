from typing import List, Optional, Union, Callable, Tuple
from datetime import date, datetime, timedelta

from pandas import DataFrame, date_range, DatetimeIndex, Series, MultiIndex, IndexSlice
from pandas.tseries.frequencies import to_offset
from numpy import ndarray, NaN, abs, around, cos, sin, unique, asarray
from math import sqrt, isnan
from copy import deepcopy
from random import uniform, gauss

import matplotlib.gridspec as gridspec
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D


def initialize_df(
    columns: List[str], start: datetime, end: datetime, resolution: timedelta) -> DataFrame:
    df = DataFrame(index=initialize_index(start, end, resolution), columns=columns)
    return df


def initialize_series(
    data: Optional[Union[Series, List[float], ndarray, float]],
    start: datetime,
    end: datetime,
    resolution: timedelta,) -> Series:
    s = Series(index=initialize_index(start, end, resolution), data=data)
    return s


def initialize_index(
    start: Union[date, datetime], end: Union[date, datetime], resolution: timedelta) -> Series:
    i = DatetimeIndex(
        start=start, end=end, freq=to_offset(resolution), closed="left", name="datetime"
    )
    return i

# def commitment_snapshots(start: Union[date, datetime], end: Union[date, datetime], ma_horizon: timedelta, ta_horizon: timedelta):
#     horizon_length = max(ma_horizon,ta_horizon)
#     horizons = int(((end-start)-horizon_length)/horizon_length)
#     snapshots = []
#     next = start
#     for h in range(0,horizons):
#         snapshots.append(next+horizon_length)
#         next = next + horizon_length
#     return snapshots

#-------------------------------------------------- Concession function --------------------------------------------------#
# Modifies input price per round based on the ration between rounds_total and rounds_left and additional decaying functions

def no_shape(rounds_total: int, rounds_left: int):
    """ Return the original values """
    return 1

def linear(rounds_total: int, rounds_left: int):
    """ Return linearly decaying values"""
    return (rounds_left/rounds_total) * 2

def root_divided_by_2(rounds_total: int, rounds_left: int):
    """ Return decaying values by using a root function """
    return (sqrt(rounds_total)/2) * (rounds_left/rounds_total)

def cos_root_divided_by_2(constant: float, rounds_total: int, rounds_left: int):
    """ Apply a cosinus function to root_divided_by_2 for some cycling behavior """
    return (sqrt(rounds_total)/2) * abs(cos(rounds_left/rounds_total))

#-------------------------------------------------- Noise function --------------------------------------------------#

def uniform_1(rounds_total:int, rounds_left:int, mean:float):
    return uniform(0,2)


def gauss_1(rounds_total:int, rounds_left:int, mean:float, std: Union[Callable, float] = uniform(0.25,0.5)):
    return round(gauss(mean, uniform(0.25,0.5)),3) * abs(-sin(2*rounds_total/rounds_left))


def gauss_2(rounds_total:int, rounds_left:int, mean:float, std: Union[Callable, float] = uniform(0.25,0.5)):
    return round(gauss(mean, uniform(0.5,0.5)),3) * abs(cos(2*rounds_total/rounds_left))


def no_noise(rounds_total:int, rounds_left:int, mean=0):
    return 0

#-------------------------------------------------- Negotiation functions --------------------------------------------------#
def create_negotiation_log(start: Union[date, datetime],
                           end: Union[date, datetime],
                           resolution: timedelta,
                           rounds_total: int,) -> DataFrame:

    ''' Returns a multiindex dataframe with inidices (datetime, rounds) and columns for prices, bids, profits, etc. '''

    logfile = DataFrame(
                index=MultiIndex.from_product(
                                     iterables=[date_range(start, end, freq=resolution),range(1, rounds_total+1)],
                                     names=['Datetime', 'Round']
                                     ),
                columns=["Clearing price", "Cleared",
                         "MA reservation price", "TA reservation price", "TA Counter reservation price",
                         "MA markup", "TA markup", "TA Counter markup",
                         "MA bid", "TA bid", "TA Counter offer",
                         "MA profit", "TA profit"]
                )
    return logfile

def start_negotiation(datetime: datetime,
                      rounds_total: int,
                      ta_policy: Callable,
                      ta_parameter: dict,
                      ma_policy: Callable,
                      ma_parameter: dict,
                      negotiation_data_df: DataFrame,
                      action_table_df: DataFrame,
                      q_table_df: DataFrame,
                      q_parameter: dict,
                      ) -> str:

    ''' Function that gets called within the trading agents step function.'''

    # placeholder dataframe
    df=negotiation_data_df
    rounds_left = rounds_total

    # Start to bargain until number of rounds_total has been exceeded or clearing price has been settled
    for round in range(1, rounds_total+1):

        round_now = rounds_total - rounds_left + 1
        # Compute round_next
        round_next = round_now + 1
        if round_now == rounds_total:
            round_next = 1

        # output stores the tuple (Res price, bid, markup)
        ma = ma_policy(rounds_total=rounds_total, rounds_left=rounds_left, ma_parameter=ma_parameter)
        # Store values
        df.loc[(datetime,round), "MA reservation price"] = ma["Reservation price"]
        df.loc[(datetime,round), "MA markup"] = around(ma["Markup"], 3)
        df.loc[(datetime,round), "MA bid"] = around(ma["Bid"] , 3)

        # Output stores the dict (bid, res, mark_up, action) given as return from get_market_agent_bid
        ta = ta_policy(rounds_total=rounds_total, rounds_left=rounds_left, ta_parameter=ta_parameter,
                       q_table_df=q_table_df, q_parameter=q_parameter)

        # Store values
        df.loc[(datetime,round), "TA reservation price"] = ta["Reservation price"]
        df.loc[(datetime,round), "TA markup"] = around(ta["Markup"], 3)
        df.loc[(datetime,round), "TA bid"] = around(ta["Bid"] , 3)
        df.loc[(datetime,round), "TA Counter offer"] = 0

        # If MAs bid is higher than TAs bids and the negotation ends.
        if ma["Bid"] >= ta["Bid"]:
            df.loc[(datetime,round), "Cleared"] = 1
            df.loc[(datetime,round), "Clearing price"] = ma["Bid"]
            df.loc[(datetime,round), "MA profit"] = ma["Reservation price"] - ma["Bid"]
            df.loc[(datetime,round), "TA profit"] = ma["Bid"] - ta["Reservation price"]

            # Update q-table in case of clearing.
            q_table_df.loc[round_now, ta["Action"]] = update_q_table(action_table_df=action_table_df, q_table_df=q_table_df,
                                                                     q_parameter=q_parameter, action=ta["Action"],
                                                                     state_now=round_now, state_next=round_next,
                                                                     reward=df.loc[(datetime,round), "TA profit"],
                                                                     negotiation_data_df=df)
            return {"Status":"Cleared", "Clearing price":ma["Bid"]}

        # TA submits a counter offer
        else:
            ta = ta_policy(rounds_total=rounds_total, rounds_left=rounds_left, ta_parameter=ta_parameter,
                           q_table_df=q_table_df, q_parameter=q_parameter)
            # Store values
            df.loc[(datetime,round), "TA Counter reservation price"] = ta["Reservation price"]
            df.loc[(datetime,round), "TA Counter markup"] = around(ta["Markup"], 3)
            df.loc[(datetime,round), "TA Counter offer"] = around(ta["Bid"] , 3)

            if ma["Bid"] >= ta["Bid"]:
                df.loc[(datetime,round), "Cleared"] = 1
                df.loc[(datetime,round), "Clearing price"] = ma["Bid"]
                df.loc[(datetime,round), "MA profit"] = ma["Reservation price"] - ma["Bid"]
                df.loc[(datetime,round), "TA profit"] = ma["Bid"] - ta["Reservation price"]

                # Update q-table in case of clearing.
                q_table_df.loc[round_now, ta["Action"]] = update_q_table(action_table_df=action_table_df, q_table_df=q_table_df,
                                                                         q_parameter=q_parameter, action=ta["Action"],
                                                                         state_now=round_now, state_next=round_next,
                                                                         reward=df.loc[(datetime,round), "TA profit"],
                                                                         negotiation_data_df=df)

                return {"Status":"Cleared", "Clearing price":ma["Bid"]}
            else:
                # Update q-table in case of no clearing
                df.loc[(datetime,round), "TA profit"] = 0
                q_table_df.loc[round_now, ta["Action"]] = update_q_table(action_table_df=action_table_df, q_table_df=q_table_df,
                                                                         q_parameter=q_parameter, action=ta["Action"],
                                                                         state_now=round_now, state_next=round_next,
                                                                         reward=df.loc[(datetime,round), "TA profit"],
                                                                         negotiation_data_df=df)
        # Decrease number of rounds left
        rounds_left -= 1

    return {"Status":"NOT CLEARED", "Clearing price":None, "TA last bid":ta["Bid"], "MA last bid":ma["Bid"]}


def update_q_table(q_table_df: DataFrame, q_parameter: dict,
                   action: str, reward: float, action_table_df: DataFrame,
                   state_now: int, state_next: int, negotiation_data_df: DataFrame):

    # Escape function if Q-learning is not applied
    if action is None:
        return

    # Update Q-Values: Q[round,action] = Q[round,action] + alpha*(reward + gamma*np.max(Q[s1,:]) - Q[s,a])
    updated_q_value = q_table_df.loc[state_now, action] + \
                      q_parameter["Alpha"] * (
                                              reward + \
                                              q_parameter["Gamma"] * \
                                              q_table_df.loc[state_next,:].max() - \
                                              q_table_df.loc[state_now, action]
                                              )

    # Count actions that have been chosen:
    action_table_df.loc[state_now, action] += 1
    return updated_q_value

def table_snapshots(snapshots: int, step_now:int, timeperiod_now: DatetimeIndex, stored_q_tables: dict, stored_action_tables: dict, q_table_now: dict, action_table_now: dict):
    if step_now in snapshots:
       stored_q_tables[(step_now,timeperiod_now)]=deepcopy(q_table_now)
       stored_action_tables[(step_now,timeperiod_now)]=deepcopy(action_table_now)
    return
