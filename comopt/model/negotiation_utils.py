from typing import List, Optional, Union, Callable, Tuple
from datetime import date, datetime, timedelta

from pandas import DataFrame, date_range, DatetimeIndex, Series, MultiIndex, IndexSlice, Index
from pandas.tseries.frequencies import to_offset
from numpy import ndarray, NaN, abs, around, cos, sin, unique, asarray
from math import sqrt, isnan
from copy import deepcopy
from random import uniform, gauss

import matplotlib.gridspec as gridspec
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

from comopt.data_structures.message_types import Prognosis, Offer
from comopt.model.plan_board import PlanBoard


# -------------------------------------------------- Negotiation related functions --------------------------------------------------#

def start_negotiation(
    description: str,
    environment_now: datetime,
    # rounds_total: int,
    # negotiation_issue: Union[Prognosis, Offer],
    # ta_policy: Callable,
    ta_parameter: dict,
    ma_parameter: dict,
    negotiation_log: DataFrame,
    plan_board: PlanBoard) -> str:

    """ Function that gets called within the trading agents step function."""

    # placeholder dataframe
    df = negotiation_log

    rounds_total = rounds_left = ta_parameter["Negotiation rounds"]

    # Start to bargain until number of rounds_total has been exceeded or clearing price has been settled
    for round in range(1, rounds_total + 1):

        round_now = rounds_total - rounds_left + 1

        # Compute round_next
        # round_next = round_now + 1
        #
        # if round_now == rounds_total:
        #     round_next = 1

        # output stores the tuple (Res price, bid, markup)
        ma = ma_parameter["Policy"](
            rounds_total=rounds_total,
            rounds_left=rounds_left,
            ma_parameter=ma_parameter,
        )
        # Store values
        df.loc[(environment_now, round), "MA reservation price"] = ma["Reservation price"]
        df.loc[(environment_now, round), "MA markup"] = around(ma["Markup"], 3)
        df.loc[(environment_now, round), "MA bid"] = around(ma["Bid"], 3)

        # ta variable stores dict with bid, res, mark_up and action.
        ta = ta_parameter["Policy"](
            description=description,
            ta_parameter=ta_parameter,
            plan_board=plan_board,
            rounds_total=rounds_total,
            rounds_left=rounds_left,
        )

        # Store values
        df.loc[(environment_now, round), "TA reservation price"] = ta["Reservation price"]
        df.loc[(environment_now, round), "TA markup"] = around(ta["Markup"], 3)
        df.loc[(environment_now, round), "TA bid"] = around(ta["Bid"], 3)
        df.loc[(environment_now, round), "TA Counter offer"] = 0

        # If MAs bid is higher than TAs bids the negotation ends.
        if ma["Bid"] >= ta["Bid"]:
            df.loc[(environment_now, round), "Cleared"] = 1
            df.loc[(environment_now, round), "Clearing price"] = ma["Bid"]
            df.loc[(environment_now, round), "MA profit"] = ma["Reservation price"] - ma["Bid"]
            df.loc[(environment_now, round), "TA profit"] = ma["Bid"] - ta["Reservation price"]

            # TODO: write decorator function to update adaptive strategy patterns
            update_adaptive_strategy_data(description=description,
                                          ta_parameter=ta_parameter,
                                          plan_board=plan_board,
                                          round_now=round_now,
                                          action=ta["Action"],
                                          profit=df.loc[(environment_now, round), "TA profit"],
                                          )

            return {"Status": "Cleared", "Clearing price": ma["Bid"]}

        # TA submits a counter offer
        else:
            ta = ta_parameter["Policy"](
                description=description,
                ta_parameter=ta_parameter,
                plan_board=plan_board,
                rounds_total=rounds_total,
                rounds_left=rounds_left,
            )
            # Store values
            df.loc[(environment_now, round), "TA Counter reservation price"] = ta[
                "Reservation price"
            ]
            df.loc[(environment_now, round), "TA Counter markup"] = around(ta["Markup"], 3)
            df.loc[(environment_now, round), "TA Counter offer"] = around(ta["Bid"], 3)

            if ma["Bid"] >= ta["Bid"]:
                df.loc[(environment_now, round), "Cleared"] = 1
                df.loc[(environment_now, round), "Clearing price"] = ma["Bid"]
                df.loc[(environment_now, round), "MA profit"] = (
                    ma["Reservation price"] - ma["Bid"]
                )
                df.loc[(environment_now, round), "TA profit"] = (
                    ma["Bid"] - ta["Reservation price"]
                )

                # Update adaptive strategy data.
                update_adaptive_strategy_data(description=description,
                                              ta_parameter=ta_parameter,
                                              plan_board=plan_board,
                                              round_now=round_now,
                                              action=ta["Action"],
                                              profit=df.loc[(environment_now, round), "TA profit"],
                                              )

                return {"Status": "Cleared", "Clearing price": ma["Bid"]}

            else:
                # Update q-table in case of no clearing
                df.loc[(environment_now, round), "TA profit"] = 0

                # Update adaptive strategy data.
                update_adaptive_strategy_data(description=description,
                                              ta_parameter=ta_parameter,
                                              plan_board=plan_board,
                                              round_now=round_now,
                                              action=ta["Action"],
                                              profit=df.loc[(environment_now, round), "TA profit"],
                                              )

                # q_table.loc[round_now, ta["Action"]] = update_q_table(
                #     action_table_df=action_table,
                #     q_table=q_table,
                #     q_parameter=q_parameter,
                #     action=ta["Action"],
                #     state_now=round_now,
                #     state_next=round_next,
                #     reward=df.loc[(datetime, round), "TA profit"],
                #     negotiation_log=df,
                # )
        # Decrease number of rounds left
        rounds_left -= 1

    return {
        "Status": "NOT CLEARED",
        "Clearing price": None,
        # "TA last bid": ta["Bid"],
        # "MA last bid": ma["Bid"],
    }

def update_adaptive_strategy_data(description: str = None,
                                  ta_parameter: dict = None,
                                  step_now: int = None,
                                  timeperiod_now: datetime = None,
                                  snapshot: bool = None,
                                  action: str = None,
                                  round_now: int = None ,
                                  round_next: int = None,
                                  profit:float = None,
                                  plan_board = None):

    # Exit if there's no adaptive strategies applied
    adaptive_strategy = ta_parameter["Policy"].__name__

    if "Simple" in adaptive_strategy:
        pass

    elif "Hill-climbing" in adaptive_strategy:
        pass

    elif "Q-learning" in adaptive_strategy:

        # Take snapshots of q-learSning related tables. Argument snapshot needs to be "True".
        if snapshot is True and step_now in plan_board.snapshot_timesteps:

            update_q_learning_table_snapshots(
                description=description,
                snapshot_timesteps=plan_board.snapshot_timesteps,
                step_now=step_now,
                timeperiod_now=timeperiod_now,
                plan_board=plan_board
            )
        else:
            update_q_learning_tables(
                description=description,
                ta_parameter=ta_parameter,
                action=action,
                state_now=round_now,
                reward=profit,
            )
    return

def update_q_learning_tables(
    description:str,
    ta_parameter: dict,
    action: str,
    reward: float,
    state_now: int,
):
    # # Escape function if Q-learning is not applied
    # if action is None:
    #     return

    if "Prognosis" in description:
        q_table = plan_board.q_table_prognosis
        action_table = plan_board.action_table_prognosis

    elif "Offer" in description:
        q_table = plan_board.q_table_flexrequest
        action_table = plan_board.action_table_flexrequest

    state_next = state_now + 1

    # Update Q-Values: Q[state_now, action] = Q[state_now, action] + alpha*(reward + gamma*np.max(Q[state_next, :]) - Q[state, action])
    q_table.loc[state_now, action] = q_table.loc[state_now, action] + ta_parameter["Alpha"] * (
        reward
        + ta_parameter["Gamma"] * q_table.loc[state_next, :].max()
        - q_table.loc[state_now, action]
    )

    # Count actions that have been chosen:
    action_table.loc[state_now, action] += 1

    return

def update_table_snapshots(
    description: str,
    plan_board):

    ''' Take snapshots of q- and action-tables at certain timeperiods for analysis purposes'''

    if "Prognosis" in description:

        q_table = plan_board.q_table_prognosis
        action_table = plan_board.action_table_prognosis

        plan_board.snapshots_q_table_prognosis[(step_now, timeperiod_now)] = deepcopy(q_table)
        plan_board.snapshots_action_table_prognosis[(step_now, timeperiod_now)] = deepcopy(action_table)

    elif "Flexrequest" in description:

        q_table = plan_board.q_table_flexrequest
        action_table = plan_board.action_table_flexrequest

        plan_board.snapshots_q_table_flexrequest[(step_now, timeperiod_now)] = deepcopy(q_table)
        plan_board.snapshots_action_table_flexrequest[(step_now, timeperiod_now)] = deepcopy(action_table)

        # table_snapshots(
        #     snapshots=self.store_table_steps,
        #     step_now=self.environment.step_now,
        #     timeperiod_now=self.environment.now,
        #     stored_q_tables=self.stored_q_tables_flexrequest_1,
        #     stored_action_tables=self.stored_action_tables_flexrequest_1,
        #     q_table_now=self.flexrequest_q_table_df_1,
        #     action_table_now=self.flexrequest_action_table_df_1,
        # )

    return


# -------------------------------------------------- Concession function --------------------------------------------------#
# Modifies input price per round based on the ration between rounds_total and rounds_left and additional decaying functions


def no_shape(rounds_total: int, rounds_left: int):
    """ Return the original values """
    return 1


def linear(rounds_total: int, rounds_left: int):
    """ Return linearly decaying values"""
    return (rounds_left / rounds_total) * 2


def root_divided_by_2(rounds_total: int, rounds_left: int):
    """ Return decaying values by using a root function """
    return (sqrt(rounds_total) / 2) * (rounds_left / rounds_total)


def cos_root_divided_by_2(constant: float, rounds_total: int, rounds_left: int):
    """ Apply a cosinus function to root_divided_by_2 for some cycling behavior """
    return (sqrt(rounds_total) / 2) * abs(cos(rounds_left / rounds_total))


# -------------------------------------------------- Noise function --------------------------------------------------#


def uniform_1(rounds_total: int, rounds_left: int, mean: float):
    return uniform(0, 2)


def gauss_1(
    rounds_total: int,
    rounds_left: int,
    mean: float,
    std: Union[Callable, float] = uniform(0.25, 0.5),
):
    return round(gauss(mean, uniform(0.25, 0.5)), 3) * abs(
        -sin(2 * rounds_total / rounds_left)
    )


def gauss_2(
    rounds_total: int,
    rounds_left: int,
    mean: float,
    std: Union[Callable, float] = uniform(0.25, 0.5),
):
    return round(gauss(mean, uniform(0.5, 0.5)), 3) * abs(
        cos(2 * rounds_total / rounds_left)
    )


def no_noise(rounds_total: int, rounds_left: int, mean=0):
    return 0
